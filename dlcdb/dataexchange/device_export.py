# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Device CSV export, shared by the legacy admin action and the assets frontend.

A column is declarative: a header plus a dotted attribute path walked from the
Device. The walk stops at the first ``None``, so a device without an active
record exports empty record cells instead of raising AttributeError.

The column set is spelled out in ``DEVICE_EXPORT_COLUMNS`` rather than derived
from ``Device._meta.fields``. Deriving it was how the original admin action
worked, and it silently exported whatever was added to the model -- including
both encryption keys -- while confusing device and record fields that happen to
share a name.
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
    path: str  # dotted attribute path from the Device, e.g. "active_record.room.number"
    formatter: Callable | None = None

    def value(self, device):
        obj = device
        for attr in self.path.split("."):
            if obj is None:
                return None
            obj = getattr(obj, attr)
        if obj is None:
            return None
        return self.formatter(obj) if self.formatter else obj

    @property
    def device_field(self):
        """The Device field this column reads from, for DEVICE_HIDE_FIELDS."""
        return self.path.split(".")[0]


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


def device_export_columns():
    """The exported columns, minus anything ``DEVICE_HIDE_FIELDS`` hides.

    The setting is honoured in the admin's list_display and fieldsets already
    (see ``core.admin.DeviceAdmin``); a field an installation keeps off the
    screen should not leave through a download either.
    """
    hidden = set(settings.DEVICE_HIDE_FIELDS or ())
    return [column for column in DEVICE_EXPORT_COLUMNS if column.device_field not in hidden]


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


def write_device_csv(queryset, columns=None):
    """Render ``queryset`` as CSV text.

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
    for device in queryset.iterator(chunk_size=2000):
        writer.writerow([_cell(column.value(device)) for column in columns])
    return buffer.getvalue()


def device_csv_response(queryset, *, slug, columns=None):
    """A CSV download of ``queryset``, headers included.

    Sent as an attachment with a quoted ``.csv`` filename so the browser hands
    it to the desktop -- whether it then prompts "open or save" or drops it
    straight into the downloads folder is a client-side preference no response
    header can decide.
    """
    filename = f"dlcdb_export_{dateformat.format(timezone.now(), 'Y-m-d_H-i-s')}_{slug}.csv"
    response = HttpResponse(
        write_device_csv(queryset, columns).encode(EXPORT_ENCODING),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
