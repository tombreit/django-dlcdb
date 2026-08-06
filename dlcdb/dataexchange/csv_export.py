# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
CSV exports of devices and lendings, shared by every surface that offers one.

A column is declarative: a header plus a dotted attribute path walked from the
row object. The walk stops at the first ``None``, so a device without an active
record exports empty record cells instead of raising AttributeError.

Two column sets live here, differing only in what they are rooted at:

* ``DEVICE_EXPORT_COLUMNS`` -- rooted at a ``Device``, used by the assets device
  list and both admin changelist actions.
* ``LENDING_EXPORT_COLUMNS`` -- rooted at a ``LentRecord``, used by the lending
  list, where the borrower and the loan details are the point of the export.

Both are spelled out rather than derived from ``_meta.fields``. Deriving them was
how the original admin action worked, and it silently exported whatever was added
to the model -- including both encryption keys -- while confusing device and
record fields that happen to share a name.
"""

import csv
import datetime
from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO

from django.conf import settings
from django.http import HttpResponse
from django.utils import dateformat, timezone


class ExcelSemicolon(csv.excel):
    """``csv.excel`` with the separator a German/European Excel expects.

    The stdlib registers only ``excel`` (comma), ``excel-tab`` and ``unix``, and
    none of them is locale-aware: Excel reads its separator from the OS list
    separator, which is ``;`` in de-DE and most of Europe. A comma file lands
    entirely in column A there. Subclassing keeps Excel's own quoting and CRLF
    conventions and changes only the delimiter.
    """

    delimiter = ";"


csv.register_dialect("excel-semicolon", ExcelSemicolon)

EXPORT_DIALECT = "excel-semicolon"

# Excel only recognises a CSV as UTF-8 if the file opens with a byte order mark;
# without one, umlauts arrive mojibake'd on a double-click. "utf-8-sig" writes
# exactly that BOM. Encoding is not part of a csv dialect, hence the separate
# constant.
EXPORT_ENCODING = "utf-8-sig"


@dataclass(frozen=True)
class Column:
    """One exported column: a header, where its value comes from, how to render."""

    header: str
    path: str  # dotted attribute path from the row, e.g. "active_record.room.number"
    formatter: Callable | None = None

    def value(self, row):
        obj = row
        for attr in self.path.split("."):
            if obj is None:
                return None
            obj = getattr(obj, attr)
        if obj is None:
            return None
        return self.formatter(obj) if self.formatter else obj


def _yes_no(value):
    """Booleans as the importer writes and reads them (dataexchange.TRUE_VALUES)."""
    return "yes" if value else "no"


# Every relation below is select_related by both callers, so an export is one
# query. A column for a relation that is NOT select_related costs one query per
# row -- add it to the caller's queryset in the same commit, or leave it out.
DEVICE_EXPORT_COLUMNS = [
    # Identity
    Column("uuid", "uuid"),
    Column("edv_id", "edv_id"),
    Column("sap_id", "sap_id"),
    Column("serial_number", "serial_number"),
    Column("device_type", "device_type.name"),
    Column("manufacturer", "manufacturer.name"),
    Column("series", "series"),
    Column("nick_name", "nick_name"),
    Column("tenant", "tenant.name"),
    Column("is_lentable", "is_lentable", _yes_no),
    Column("is_licence", "is_licence", _yes_no),
    # Procurement and contract
    Column("supplier", "supplier.name"),
    Column("order_number", "order_number"),
    Column("cost_centre", "cost_centre"),
    Column("book_value", "book_value"),
    Column("purchase_date", "purchase_date"),
    Column("warranty_expiration_date", "warranty_expiration_date"),
    Column("contract_start_date", "contract_start_date"),
    Column("contract_expiration_date", "contract_expiration_date"),
    Column("contract_termination_date", "contract_termination_date"),
    Column("procurement_note", "procurement_note"),
    # Network
    Column("mac_address", "mac_address"),
    Column("extra_mac_addresses", "extra_mac_addresses"),
    # People and notes. The device's own note, not the active record's -- the
    # export this replaced silently substituted the record's.
    Column("contact_person_internal", "contact_person_internal"),
    Column("url", "url"),
    Column("note", "note"),
    # The active record, flattened onto the device row under a record_ prefix so
    # no column is ambiguous about which model it came from. Room by number and
    # inventory by name: their __str__ adds a nickname / a translated prefix.
    Column("record_type", "active_record.record_type"),
    Column("record_room", "active_record.room.number"),
    Column("record_person", "active_record.person"),
    Column("record_inventory", "active_record.inventory.name"),
    Column("record_lent_start_date", "active_record.lent_start_date"),
    Column("record_lent_desired_end_date", "active_record.lent_desired_end_date"),
    Column("record_lent_end_date", "active_record.lent_end_date"),
    Column("record_note", "active_record.note"),
    Column("record_created_at", "active_record.created_at"),
    # Audit
    Column("is_imported", "is_imported", _yes_no),
    Column("username", "username"),
    Column("created_at", "created_at"),
    Column("modified_at", "modified_at"),
]

# Deliberately not exported:
#   machine_encryption_key, backup_encryption_key -- secrets. The frontend hides
#       them from users who may only view a device, so a view_device-gated
#       download must not hand them over either.
#   qrcode -- a storage path, useless off-server; uuid is the real identity.
#   imported_by, user, deleted_by -- FK pks, and not select_related: one query
#       per row each. The denormalized `username` and the `is_imported` flag
#       carry the same information.
#   id -- an internal surrogate key; uuid is the stable public identifier.
#   active_record -- the record's pk. `record_type` says something useful instead.
#   deleted_at -- always empty: Device.objects excludes soft-deleted rows.
#   is_legacy -- an internal flag, surfaced nowhere in the frontend.

# What a caller must select_related for the export to stay at one query. Kept
# beside the columns so the two are edited together; ``assets._device_queryset``
# already joins all of these for the list page itself.
EXPORT_RELATIONS = (
    "device_type",
    "manufacturer",
    "supplier",
    "contact_person_internal",
    "tenant",
    "active_record",
    "active_record__room",
    "active_record__person",
    "active_record__inventory",
)


# Rooted at a LentRecord, one row per row of the lending list. That list shows a
# device's *current* record (the manager filters is_active=True), so a row is a
# lending, an available device, or occasionally a lost/ordered one -- the
# record_type column says which.
#
# ``state`` and ``is_overdue`` read annotations, so this set only works against a
# queryset from ``lending.views._lending_filter``. ``Column.value`` uses a strict
# getattr, so a queryset missing them fails loudly instead of quietly emitting an
# empty column.
LENDING_EXPORT_COLUMNS = [
    # The device being lent
    Column("edv_id", "device.edv_id"),
    Column("sap_id", "device.sap_id"),
    Column("serial_number", "device.serial_number"),
    Column("device_type", "device.device_type.name"),
    Column("manufacturer", "device.manufacturer.name"),
    Column("series", "device.series"),
    Column("tenant", "device.tenant.name"),
    # State, as the page's badge shows it
    Column("record_type", "record_type"),
    Column("state", "lent_state"),
    Column("is_overdue", "is_overdue", _yes_no),
    Column("room", "room.number"),
    # Who has it
    Column("person", "person"),
    Column("person_email", "person.email"),
    Column("organizational_unit", "person.organizational_unit.name"),
    # The loan itself. lent_end_date is deliberately absent: a returned lending is
    # never active, and this list only ever shows active records, so the column
    # would be empty in every row.
    Column("lent_start_date", "lent_start_date"),
    Column("lent_desired_end_date", "lent_desired_end_date"),
    Column("lent_reason", "lent_reason"),
    Column("lent_accessories", "lent_accessories"),
    Column("lent_note", "lent_note"),
    Column("record_note", "note"),
    # Audit
    Column("username", "username"),
    Column("created_at", "created_at"),
    Column("modified_at", "modified_at"),
]

# The lending list itself joins device, device__manufacturer, device__device_type,
# person and room; device__tenant and person__organizational_unit are needed only
# by the export, which applies this itself rather than widening the list query for
# columns the list does not render.
LENDING_EXPORT_RELATIONS = (
    "device",
    "device__device_type",
    "device__manufacturer",
    "device__tenant",
    "person",
    "person__organizational_unit",
    "room",
)


def visible_columns(columns, *, device_prefix):
    """``columns`` minus any exposing a Device field that DEVICE_HIDE_FIELDS hides.

    The setting names Device fields, and it is honoured in the admin's
    list_display and fieldsets already (see ``core.admin.DeviceAdmin``): a field
    an installation keeps off the screen should not leave through a download
    either.

    ``device_prefix`` says how the column set reaches the Device -- "" when the
    rows *are* devices, "device." when they are records. It has to be explicit:
    ``Device`` and ``Record`` share field names (both have ``note``), so guessing
    a column's root from its path alone would hide the wrong ones.
    """
    hidden = set(settings.DEVICE_HIDE_FIELDS or ())
    if not hidden:
        return list(columns)

    def device_field(path):
        """The Device field this path exposes, or None if it touches no device."""
        if not path.startswith(device_prefix):
            return None
        return path[len(device_prefix) :].split(".")[0]

    return [column for column in columns if device_field(column.path) not in hidden]


def device_export_columns():
    """The device columns a request may see."""
    return visible_columns(DEVICE_EXPORT_COLUMNS, device_prefix="")


def lending_export_columns():
    """The lending columns a request may see."""
    return visible_columns(LENDING_EXPORT_COLUMNS, device_prefix="device.")


def _cell(value):
    """Render one value.

    Only datetimes need explicit handling; ``date`` already stringifies as ISO
    (which Excel parses), and everything else is left to ``csv``'s own ``str()``,
    including ``None``, which becomes an empty cell.

    Timestamps are localized, unlike in the export this replaced: it printed the
    raw UTC the ORM hands back, so a German user reading a device's history saw
    times two hours off the ones the admin showed them.
    """
    if isinstance(value, datetime.datetime):  # checked before date: it is a subclass
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return f"{value:%Y-%m-%d %H:%M}"
    return value


def write_csv(queryset, columns=None):
    """Render ``queryset`` as CSV text, one row per object.

    ``columns`` defaults to the device set, which is what most callers want; the
    lending list passes ``lending_export_columns()``.

    ``.iterator()`` keeps the queryset result cache out of memory and enables
    server-side cursors on PostgreSQL, which is safe because callers use only
    ``select_related``. The text itself is accumulated in a buffer: a full
    unfiltered export is single-digit MB, and the device list page already
    renders the same rows as HTML under ``?show_all=1``.
    """
    columns = device_export_columns() if columns is None else columns

    buffer = StringIO()
    writer = csv.writer(buffer, dialect=EXPORT_DIALECT)
    writer.writerow([column.header for column in columns])
    for row in queryset.iterator(chunk_size=2000):
        writer.writerow([_cell(column.value(row)) for column in columns])
    return buffer.getvalue()


def csv_response(queryset, *, slug, columns=None):
    """A CSV download of ``queryset``, headers included.

    Sent as an attachment with a quoted ``.csv`` filename so the browser hands
    it to the desktop -- whether it then prompts "open or save" or drops it
    straight into the downloads folder is a client-side preference no response
    header can decide.
    """
    filename = f"dlcdb_export_{dateformat.format(timezone.now(), 'Y-m-d_H-i-s')}_{slug}.csv"
    response = HttpResponse(
        write_csv(queryset, columns).encode(EXPORT_ENCODING),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
