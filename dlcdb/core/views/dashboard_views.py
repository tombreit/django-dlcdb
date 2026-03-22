# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.apps import apps
from django.utils.text import slugify

from ..utils.helpers import get_has_note_badge, get_icon_for_class
from ..models import Inventory
from .. import stats


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
            self.create_tile(model_name="core.lostrecord", url="admin:core_lostrecord_changelist"),
            self.create_tile(model_name="core.inventory", url="inventory:inventorize-room-list")
            if Inventory.objects.filter(is_active=True)
            else None,
        ]

        context.update(
            dict(
                record_fraction_html=stats.get_record_fraction_html(tenant=self.request.tenant),
                device_type_html=stats.get_device_type_html(tenant=self.request.tenant),
                record_timeline_html=stats.get_record_timeline_html(tenant=self.request.tenant),
                tiles=filter(None, tiles),
            )
        )
        return context
