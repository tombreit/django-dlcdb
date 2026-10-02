# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from collections import defaultdict

import plotly.graph_objects as go
import plotly.io as pio
from django.db.models import Count, Q
from django.utils import timezone

from dlcdb.core.models import (
    DeviceType,
    Record,
)

# Shared plotly config: hide modebar entirely
PLOTLY_CONFIG = {"displayModeBar": False}

# Shared layout defaults
PLOTLY_LAYOUT = dict(
    font=dict(family="Roboto, sans-serif"),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)

# Color palette for bar charts
COLORS = {
    "primary": "#5b69bc",
    "primary_light": "#8b96d4",
    "accent": "#e8634a",
    "accent_light": "#f09a88",
    "muted": "#9e9e9e",
}


def _to_html(fig):
    """Render a plotly figure to HTML with shared config."""
    return pio.to_html(fig, full_html=False, include_plotlyjs=False, config=PLOTLY_CONFIG)


def _month_index(moment):
    """Months since year 0, so a span of months is a plain range()."""
    return moment.year * 12 + moment.month - 1


def devices_per_month(records, *, now):
    """
    {record_type: {"YYYY-MM": device_ids}} from
    ``(device_id, record_type, created_at, effective_until)`` rows.

    A record owns month M if it is still the active record at the end of M:
    from the month it was created up to the month before it was superseded, or
    through the current month while active. A REMOVED record counts once, in the
    month of the removal.
    """
    type_month_devices = defaultdict(lambda: defaultdict(set))
    for device_id, record_type, created_at, effective_until in records:
        first = _month_index(created_at)
        if record_type == Record.REMOVED:
            last = first
        else:
            last = _month_index(effective_until) - 1 if effective_until else _month_index(now)
        for index in range(first, last + 1):
            type_month_devices[record_type][f"{index // 12}-{index % 12 + 1:02d}"].add(device_id)
    return type_month_devices


def get_record_fraction_html(*, tenants):
    """
    Returns a plotly HTML div showing the fraction of active records by type.
    """
    labels = ["Lokalisiert", "Verliehen", "Nicht auffindbar", "Entfernt"]
    base = Record.objects.filter(is_active=True, device__tenant__in=tenants)

    # "Verliehen" mirrors LentRecordManager's WHERE (core/models/prx_lentrecord.py):
    # active + lentable device, excluding removed/licence — NOT a pure record_type=LENT count.
    lent_filter = Q(device__is_lentable=True) & ~Q(record_type=Record.REMOVED) & ~Q(device__is_licence=True)

    counts_map = base.aggregate(
        inroom=Count("pk", filter=Q(record_type=Record.INROOM)),
        lent=Count("pk", filter=lent_filter),
        lost=Count("pk", filter=Q(record_type=Record.LOST)),
        removed=Count("pk", filter=Q(record_type=Record.REMOVED)),
    )
    counts = [counts_map["inroom"], counts_map["lent"], counts_map["lost"], counts_map["removed"]]

    colors = [COLORS["primary"], COLORS["accent"], COLORS["muted"], COLORS["accent_light"]]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker=dict(color=colors, cornerradius=4),
            text=counts,
            textposition="auto",
            textfont=dict(color="white", size=13),
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=250,
        margin=dict(l=10, r=30, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False),
        bargap=0.3,
    )
    return _to_html(fig)


def get_device_type_html(*, tenants):
    """
    Returns a plotly HTML div showing device counts by type (>10 devices).
    """
    count_filter = Q(device__tenant__in=tenants)
    device_types_qs = (
        DeviceType.objects.annotate(count=Count("device", filter=count_filter)).exclude(count__lt=10).order_by("count")
    )

    labels = [dt.name for dt in device_types_qs]
    counts = [dt.count for dt in device_types_qs]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[[0, COLORS["primary_light"]], [1, COLORS["primary"]]],
                cornerradius=4,
            ),
            text=counts,
            textposition="outside",
            textfont=dict(size=11),
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=max(300, len(labels) * 28),
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        bargap=0.2,
    )
    return _to_html(fig)


def get_record_timeline_html(*, tenants):
    """
    Returns a plotly HTML div showing the number of devices with each record
    type (LENT, INROOM, LOST) active per month over time, and the removals
    (REMOVED) per month.
    """
    chart_types = [Record.LENT, Record.INROOM, Record.LOST, Record.REMOVED]
    records = Record.objects.filter(device__tenant__in=tenants, record_type__in=chart_types).values_list(
        "device_id", "record_type", "created_at", "effective_until"
    )
    type_month_devices = devices_per_month(records, now=timezone.now())

    type_labels = {
        Record.LENT: "Verliehen",
        Record.INROOM: "Lokalisiert",
        Record.LOST: "Nicht auffindbar",
        Record.REMOVED: "Entfernt",
    }

    trace_styles = {
        Record.LENT: dict(line=dict(color=COLORS["accent"], width=2.5)),
        Record.INROOM: dict(
            line=dict(color=COLORS["primary"], width=2.5), fill="tozeroy", fillcolor="rgba(91,105,188,0.12)"
        ),
        Record.LOST: dict(line=dict(color=COLORS["accent_light"], width=2.5)),
        Record.REMOVED: dict(marker=dict(color=COLORS["muted"], cornerradius=3, opacity=0.6)),
    }

    fig = go.Figure()
    for rtype in chart_types:
        month_devices = type_month_devices[rtype]
        months = sorted(month_devices.keys())
        counts = [len(month_devices[m]) for m in months]
        if rtype == Record.REMOVED:
            fig.add_trace(go.Bar(x=months, y=counts, name=type_labels[rtype], **trace_styles[rtype]))
        else:
            fig.add_trace(go.Scatter(x=months, y=counts, mode="lines", name=type_labels[rtype], **trace_styles[rtype]))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        xaxis_title="Monat",
        yaxis_title="Anzahl Geräte",
        height=350,
        margin=dict(l=50, r=20, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0.06)", zeroline=False),
    )
    return _to_html(fig)
