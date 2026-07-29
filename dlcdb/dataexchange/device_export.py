# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Device CSV export, shared by the legacy admin action and the assets frontend.

A column is declarative: a header plus a dotted attribute path walked from the
Device. The walk stops at the first ``None``, so a device without an active
record exports empty record cells instead of raising AttributeError -- the one
behaviour that changed when this moved out of ``core.admin.base_admin``.

The column list is derived from ``Device._meta.fields`` rather than spelled out,
which reproduces the historical export exactly, quirks included (see
``legacy_device_columns``). Curating it is a separate, later change.
"""

import csv
import datetime
from dataclasses import dataclass
from io import StringIO

from django.http import HttpResponse
from django.utils import dateformat, timezone

from dlcdb.core.models import Device, Record

# Names that live on both models, because both inherit AuditBaseModel. The
# historical export resolves these through the active record, not the device.
_RECORD_FIELD_NAMES = frozenset(field.name for field in Record._meta.fields)


@dataclass(frozen=True)
class Column:
    """One exported column: a header and where its value comes from."""

    header: str
    path: str  # dotted attribute path from the Device, e.g. "active_record.room"

    def value(self, device):
        obj = device
        for attr in self.path.split("."):
            if obj is None:
                return None
            obj = getattr(obj, attr)
        return obj


def legacy_device_columns(*, extra=()):
    """``Device._meta.fields`` + ``extra`` + ``room`` and ``created_at``.

    The shape operators' spreadsheets and scripts have consumed for years, so
    three quirks are reproduced deliberately rather than fixed here:

    * The six names ``Device`` and ``Record`` share (id, user, username,
      created_at, modified_at, note) resolve through ``active_record``. So
      ``id`` carries the record's pk and ``note`` the record's note; the
      device's own id and note are never exported.
    * ``created_at`` is appended although it is already present, so it appears
      twice -- in the header and in every row.
    * ``active_record`` resolves to the ``Record`` object, whose ``__str__`` is
      its pk, making it a second copy of the ``id`` column.
    """
    names = [field.name for field in Device._meta.fields] + [*extra, "room", "created_at"]
    return [
        Column(
            header=name,
            path=f"active_record.{name}" if name in _RECORD_FIELD_NAMES else name,
        )
        for name in names
    ]


def _cell(value):
    """Render one value.

    Only datetimes need explicit handling; ``date`` already stringifies as ISO
    and everything else is left to ``csv``'s own ``str()``, including ``None``,
    which becomes an empty cell. Datetimes are formatted as they come off the
    ORM (UTC under ``USE_TZ``), matching the export this replaced.
    """
    if isinstance(value, datetime.datetime):
        return f"{value:%Y-%m-%d %H:%M}"
    return value


def write_device_csv(queryset, columns, *, dialect="excel-tab", quoting=csv.QUOTE_ALL):
    """Render ``queryset`` as CSV text.

    The dialect defaults to the historical tab-separated one. ``.iterator()``
    keeps the queryset result cache out of memory and enables server-side
    cursors on PostgreSQL, which is safe because callers use only
    ``select_related``. The text itself is accumulated in a buffer: a full
    unfiltered export is single-digit MB, and the device list page already
    renders the same rows as HTML under ``?show_all=1``.
    """
    buffer = StringIO()
    writer = csv.writer(buffer, dialect=dialect, quoting=quoting)
    writer.writerow([column.header for column in columns])
    for device in queryset.iterator(chunk_size=2000):
        writer.writerow([_cell(column.value(device)) for column in columns])
    return buffer.getvalue()


def device_csv_response(queryset, columns, *, slug, **writer_kwargs):
    """A CSV download of ``queryset``, headers included.

    Filename shape ``dlcdb_export_<Y-m-d_H-i-s>_<slug>.csv``, unchanged from the
    admin action this was extracted from.
    """
    filename = f"dlcdb_export_{dateformat.format(timezone.now(), 'Y-m-d_H-i-s')}_{slug}.csv"
    response = HttpResponse(
        write_device_csv(queryset, columns, **writer_kwargs),
        content_type="text/csv",
    )
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response
