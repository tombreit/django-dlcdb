# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from collections import defaultdict

import plotly.graph_objects as go
import plotly.io as pio
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from dlcdb.core import lifecycle
from dlcdb.core.models import (
    DeviceType,
    Record,
)
from dlcdb.theme.lifecycle_display import state_color

# Shared plotly config: hide modebar entirely
PLOTLY_CONFIG = {"displayModeBar": False}

# Shared layout defaults: the theme's typeface on a transparent ground, so the
# chart sits on its panel. Text colours are set per colour mode in
# _dashboard.scss: a figure is rendered once for both modes.
PLOTLY_LAYOUT = dict(
    font=dict(family='"IBM Plex Sans Variable", system-ui, sans-serif', size=13),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)

# Gridlines: a hairline that reads on the light and on the dark panel.
GRID_COLOR = "rgba(128,128,128,0.25)"

# Mark colour per Bootstrap colour name, so a state wears the colour of its badge
# (theme.lifecycle_display.STATE_COLORS). Bootstrap 5.3's palette, except for
# warning: $yellow-600 instead of $yellow, which is too light for a mark on the
# light panel. Checked with the dataviz palette validator on both panel colours:
# lightness band, colour-blind and normal-vision separation pass; contrast stays
# below 3:1 for some marks, so every chart labels its values or has a legend and
# end labels. The grey of "removed" is the de-emphasised state on purpose.
MARK_COLORS = {
    "info": "#0dcaf0",
    "success": "#198754",
    "warning": "#cc9a06",
    "danger": "#dc3545",
    "secondary": "#6c757d",
}

# A single series (devices by type): the indigo one step lighter than the
# theme's primary, which keeps about 3:1 on the light and the dark panel.
SERIES_COLOR = "#6366f1"

# Bars are 22px thick in a 36px slot: thin marks, the rest is air. A chart is
# as tall as its bars need, so the bars keep that thickness.
BAR_SLOT = 36
BAR_GAP = 0.4

# The device type chart leaves out types with fewer devices.
DEVICE_TYPE_MIN_COUNT = 10


def _state_color(state):
    return MARK_COLORS[state_color(state)]


def _state_label(state):
    return str(lifecycle.STATES[state].label)


def _hex_to_rgba(color, alpha):
    red, green, blue = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red},{green},{blue},{alpha})"


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


def active_record_counts(*, tenants):
    """
    How many of the tenants' devices are in each state the record chart shows, counted
    by their active record. Lent means a LENT record; ``LentRecord.objects`` would also
    count the available and lost lentable devices.
    """
    return Record.objects.filter(is_active=True, device__tenant__in=tenants).aggregate(
        inroom=Count("pk", filter=Q(record_type=Record.INROOM)),
        lent=Count("pk", filter=Q(record_type=Record.LENT)),
        lost=Count("pk", filter=Q(record_type=Record.LOST)),
        removed=Count("pk", filter=Q(record_type=Record.REMOVED)),
    )


def get_record_fraction_html(*, tenants):
    """
    Returns a plotly HTML div with the tenants' devices per state, counted by
    their active record, in lifecycle order and in the colours of the state
    badges.
    """
    states = [Record.INROOM, Record.LENT, Record.LOST, Record.REMOVED]
    counts_map = active_record_counts(tenants=tenants)
    counts = [counts_map[state.lower()] for state in states]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=[_state_label(state) for state in states],
            orientation="h",
            marker=dict(color=[_state_color(state) for state in states], cornerradius=4),
            text=counts,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=len(states) * BAR_SLOT + 20,
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        # Lifecycle order top-down; a categorical axis starts at the bottom.
        yaxis=dict(showgrid=False, autorange="reversed"),
        bargap=BAR_GAP,
    )
    return _to_html(fig)


def get_device_type_html(*, tenants):
    """
    Returns a plotly HTML div showing device counts by type, for types with at
    least ``DEVICE_TYPE_MIN_COUNT`` devices, or "" when there is none.
    """
    count_filter = Q(device__tenant__in=tenants)
    device_types_qs = (
        DeviceType.objects.annotate(count=Count("device", filter=count_filter))
        .exclude(count__lt=DEVICE_TYPE_MIN_COUNT)
        .order_by("count")
    )

    labels = [dt.name for dt in device_types_qs]
    counts = [dt.count for dt in device_types_qs]
    if not labels:
        return ""

    # One series in one colour: bar length already shows the count.
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker=dict(color=SERIES_COLOR, cornerradius=4),
            text=counts,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=len(labels) * BAR_SLOT + 20,
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False),
        bargap=BAR_GAP,
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

    fig = go.Figure()
    for rtype in chart_types:
        month_devices = type_month_devices[rtype]
        months = sorted(month_devices.keys())
        counts = [len(month_devices[m]) for m in months]
        color = _state_color(rtype)
        if rtype == Record.REMOVED:
            fig.add_trace(
                go.Bar(x=months, y=counts, name=_state_label(rtype), marker=dict(color=color, cornerradius=4))
            )
            continue
        # The devices in a room are most of the stock: their line gets a 10%
        # wash underneath, the others stay plain lines.
        area = dict(fill="tozeroy", fillcolor=_hex_to_rgba(color, 0.1)) if rtype == Record.INROOM else {}
        fig.add_trace(
            go.Scatter(
                x=months,
                y=counts,
                mode="lines",
                name=_state_label(rtype),
                line=dict(color=color, width=2),
                **area,
            )
        )
        # The current value at the end of each line, in text colour.
        if months:
            fig.add_annotation(
                x=months[-1], y=counts[-1], text=str(counts[-1]), showarrow=False, xanchor="left", xshift=6
            )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        yaxis_title=_("Devices"),
        height=350,
        margin=dict(l=50, r=40, t=10, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=GRID_COLOR, gridwidth=1, zeroline=False),
    )
    return _to_html(fig)
