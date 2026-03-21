# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from collections import defaultdict

from django.db.models import Count
from django.utils import timezone

import plotly.graph_objects as go
import plotly.io as pio

from .models.device import Device
from .models.device_type import DeviceType
from .models.record import Record

from .models.prx_inroomrecord import InRoomRecord
from .models.prx_lentrecord import LentRecord
from .models.prx_lostrecord import LostRecord
from .models.prx_removedrecord import RemovedRecord


def get_record_fraction_html():
    """
    Returns a plotly HTML div showing the fraction of active records by type.
    """
    labels = ["Lokalisiert", "Verliehen", "Nicht auffindbar", "Entfernt"]
    counts = [
        InRoomRecord.objects.filter(is_active=True).count(),
        LentRecord.objects.filter(is_active=True).count(),
        LostRecord.objects.filter(is_active=True).count(),
        RemovedRecord.objects.filter(is_active=True).count(),
    ]

    fig = go.Figure(go.Bar(x=counts, y=labels, orientation="h"))
    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def get_device_type_html():
    """
    Returns a plotly HTML div showing device counts by type (>10 devices).
    """
    device_types_qs = DeviceType.objects.annotate(count=Count("device")).exclude(count__lt=10).order_by("count")

    labels = [dt.name for dt in device_types_qs]
    counts = [dt.count for dt in device_types_qs]

    fig = go.Figure(go.Bar(x=counts, y=labels, orientation="h"))
    fig.update_layout(
        height=max(250, len(labels) * 25),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def get_record_timeline_html():
    """
    Returns a plotly HTML div showing the number of devices with each record
    type (LENT, INROOM, REMOVED) active per month over time.

    Uses a single query fetching all records ordered by device and time.
    Each record's active period is derived from the next record's created_at
    for the same device (not from effective_until, which is unreliable due to
    Record.save() overwriting it on ALL previous records).
    """
    now = timezone.now()
    chart_types = [Record.LENT, Record.INROOM, Record.REMOVED]

    # Fetch ALL record types — we need ORDERED/LOST too to know when
    # an INROOM/LENT period ends.
    records = Record.objects.order_by("device_id", "created_at").values_list("device_id", "record_type", "created_at")

    # Group records by device, derive active periods from consecutive records
    # {record_type: {month_key: set(device_ids)}}
    type_month_devices = defaultdict(lambda: defaultdict(set))

    # Walk through records grouped by device
    current_device = None
    device_records = []

    def _process_device_records(device_id, dev_records):
        for i, (rtype, start) in enumerate(dev_records):
            if rtype == Record.REMOVED:
                month_key = f"{start.year}-{start.month:02d}"
                type_month_devices[rtype][month_key].add(device_id)
                continue

            if rtype not in (Record.LENT, Record.INROOM):
                continue

            # Determine end month (inclusive) for this record's active period.
            # Use "state at end of month" semantics: a record owns month M if
            # it is still the active record at the end of that month.
            year, month = start.year, start.month
            if i + 1 < len(dev_records):
                # Exclusive boundary: the month the next record starts is owned
                # by the next record, so this record covers up to the month before.
                next_start = dev_records[i + 1][1]
                end_year, end_month = next_start.year, next_start.month - 1
                if end_month < 1:
                    end_month = 12
                    end_year -= 1
            else:
                # Last record: still active through current month
                end_year, end_month = now.year, now.month

            while (year, month) <= (end_year, end_month):
                month_key = f"{year}-{month:02d}"
                type_month_devices[rtype][month_key].add(device_id)
                month += 1
                if month > 12:
                    month = 1
                    year += 1

    for device_id, record_type, created_at in records:
        if device_id != current_device:
            if current_device is not None:
                _process_device_records(current_device, device_records)
            current_device = device_id
            device_records = []
        device_records.append((record_type, created_at))

    if current_device is not None:
        _process_device_records(current_device, device_records)

    type_labels = {
        Record.LENT: "Verliehen",
        Record.INROOM: "Lokalisiert",
        Record.REMOVED: "Entfernt",
    }

    fig = go.Figure()
    for rtype in chart_types:
        month_devices = type_month_devices[rtype]
        months = sorted(month_devices.keys())
        counts = [len(month_devices[m]) for m in months]
        if rtype == Record.REMOVED:
            fig.add_trace(go.Bar(x=months, y=counts, name=type_labels[rtype]))
        else:
            fig.add_trace(go.Scatter(x=months, y=counts, mode="lines", name=type_labels[rtype]))

    fig.update_layout(
        xaxis_title="Monat",
        yaxis_title="Anzahl Geräte",
        height=400,
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def get_devices_by_series_data():
    """
    Returns a plotly HTML div showing device counts by series.
    """
    qs = Device.objects.values("series").annotate(total=Count("series"))

    labels = [elem["series"] for elem in qs]
    counts = [elem["total"] for elem in qs]

    fig = go.Figure(go.Bar(x=counts, y=labels, orientation="h"))
    fig.update_layout(
        height=max(250, len(labels) * 25),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)
