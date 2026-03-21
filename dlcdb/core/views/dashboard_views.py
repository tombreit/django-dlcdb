# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from collections import defaultdict
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.apps import apps
from django.utils.text import slugify

import plotly.graph_objects as go
import plotly.io as pio

from ..utils.helpers import get_has_note_badge, get_icon_for_class
from ..models import Inventory
from .. import stats


def _build_sparkline_html(model_class_name):
    """Build a small plotly sparkline HTML div for a record type's timeline."""
    ModelClass = apps.get_model(model_class_name)
    qs = ModelClass.objects.order_by("created_at")

    if not qs.exists():
        return None

    earliest = qs.earliest("created_at")
    latest = qs.latest("created_at")

    def _populate_date_range(earliest_dt, latest_dt):
        date_keys = defaultdict(set)
        for year in range(earliest_dt.year, latest_dt.year + 1):
            start_month = earliest_dt.month if year == earliest_dt.year else 1
            end_month = latest_dt.month if year == latest_dt.year else 12
            for month in range(start_month, end_month + 1):
                date_keys[f"{year}-{month:02d}"]
        return date_keys

    date_keys_dict = _populate_date_range(earliest.created_at, latest.created_at)

    for record in qs:
        end_date = record.effective_until if record.effective_until else latest.created_at
        valid_months = list(_populate_date_range(record.created_at, end_date).keys())
        for month_key in valid_months:
            date_keys_dict[month_key].add(record.device_id)

    dates = sorted(date_keys_dict.keys())
    counts = [len(date_keys_dict[d]) for d in dates]

    fig = go.Figure(go.Scatter(x=dates, y=counts, mode="lines", line=dict(color="white", width=3)))
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "admin/dashboard.html"

    @staticmethod
    def create_tile(*, model_name, url, chart_html=None):
        from ..models import Record

        model_class_name = model_name
        ModelClass = apps.get_model(model_class_name)

        obj_notes_count = None
        obj_count = ModelClass.objects.all().count()
        human_model_name = ModelClass._meta.verbose_name_plural if obj_count >= 2 else ModelClass._meta.verbose_name
        model_class_icon = get_icon_for_class(model_name)

        if hasattr(ModelClass, "note"):
            obj_notes_count = ModelClass.objects.exclude(note__exact="").count()
            obj_notes_count = obj_notes_count if obj_notes_count >= 1 else ""

        if model_name == "core.lentrecord":
            lented_count = ModelClass.objects.filter(record_type=Record.LENT).count()
            obj_count = f"{lented_count} / {obj_count}"
        elif model_name == "core.inventory":
            obj_count = ModelClass.objects.filter(is_active=True).first()

        template = "admin/dashboard_tile.html"
        context = {
            "css_classes": "btn btn-lg btn-{}".format("warning" if obj_notes_count else "primary"),
            "url": reverse_lazy(url),
            "query_params": "has_note=has_note" if obj_notes_count else "",
            "text": human_model_name,
            "hover_text": f"{obj_notes_count} {human_model_name} with notes" if obj_notes_count else "",
            "obj_count": obj_count,
            "model_class_icon": model_class_icon,
            "model_name_slug": slugify(model_name),
            "chart_html": chart_html,
        }

        if not any(
            [
                model_name == "core.device",
                model_name == "core.lentrecord",
                model_name == "core.licencerecord",
            ]
        ):
            context.update(
                {
                    "badge": get_has_note_badge(obj_type=model_name, has_note=obj_notes_count)
                    if obj_notes_count
                    else "",
                }
            )

        return render_to_string(template, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tiles = [
            self.create_tile(model_name="core.device", url="admin:core_device_changelist"),
            self.create_tile(model_name="core.lentrecord", url="admin:core_lentrecord_changelist"),
            self.create_tile(model_name="core.room", url="admin:core_room_changelist"),
            self.create_tile(model_name="core.devicetype", url="admin:core_devicetype_changelist"),
            self.create_tile(model_name="core.licencerecord", url="licenses:index"),
            self.create_tile(model_name="smallstuff.assignedthing", url="smallstuff:person_search"),
            self.create_tile(
                model_name="core.lostrecord",
                url="admin:core_lostrecord_changelist",
                chart_html=_build_sparkline_html("core.lostrecord"),
            ),
            self.create_tile(model_name="core.inventory", url="inventory:inventorize-room-list")
            if Inventory.objects.filter(is_active=True)
            else None,
        ]

        context.update(
            dict(
                record_fraction_html=stats.get_record_fraction_html(),
                device_type_html=stats.get_device_type_html(),
                tiles=filter(None, tiles),
            )
        )
        return context
