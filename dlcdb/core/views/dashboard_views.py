import json
import string

from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.apps import apps

from ..utils.helpers import get_has_note_badge, get_icon_for_class
from ..models.inventory import Inventory
from ..models import Device

from dlcdb.core import stats


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/dashboard.html'

    @staticmethod
    def create_tile(*, model_name, changelist_url):
        human_model_name = model_name.title().replace('_', ' ')
        model_class_name = string.capwords(model_name, sep="_").replace("_", "")
        ModelClass = apps.get_model(f"core.{model_class_name}")
        obj_notes_count = ModelClass.objects.exclude(note__exact="").count()
        obj_notes_count = obj_notes_count if obj_notes_count >= 1 else ""

        obj_count = ModelClass.objects.all().count()
        model_class_icon = get_icon_for_class(model_name)

        template = 'admin/dashboard_tile.html'
        context = {
            "css_classes": "btn btn-lg btn-{}".format("warning" if obj_notes_count else "primary"),
            "url": reverse_lazy(changelist_url),
            "query_params": "has_note=has_note" if obj_notes_count else "",
            "text": human_model_name,
            "hover_text": f"{obj_notes_count} {human_model_name} with notes" if obj_notes_count else "",
            "obj_count": obj_count,
            "model_class_icon": model_class_icon,
        }

        if not ModelClass == Device:
            context.update({
                "badge": get_has_note_badge(obj_type=model_name, has_note=obj_notes_count) if obj_notes_count else "",
            })
        return render_to_string(template, context)

    @staticmethod
    def create_hasnote_button(*, model_name, changelist_url):
        human_model_name = model_name.title().replace('_', ' ')
        model_class_name = string.capwords(model_name, sep="_").replace("_", "")
        ModelClass = apps.get_model(f"core.{model_class_name}")
        obj_notes_count = ModelClass.objects.exclude(note__exact="").count()
        obj_notes_count = obj_notes_count if obj_notes_count >= 1 else ""

        button_template = 'admin/dashboard_button.html'
        context = {
            "css_classes": "btn btn-lg btn-{}".format("warning" if obj_notes_count else "primary"),
            "url": reverse_lazy(changelist_url),
            "query_params": "has_note=has_note" if obj_notes_count else "",
            "badge": get_has_note_badge(obj_type=model_name, has_note=obj_notes_count) if obj_notes_count else "",
            "text": human_model_name,
            "hover_text": f"{obj_notes_count} {human_model_name} with notes" if obj_notes_count else "",
        }
        return render_to_string(button_template, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        custom_buttons = [
            self.create_hasnote_button(model_name="room", changelist_url="admin:core_room_changelist"),
            self.create_hasnote_button(model_name="device_type", changelist_url="admin:core_devicetype_changelist"),
        ]

        tiles = [
            self.create_tile(model_name="device", changelist_url="admin:core_device_changelist"),
            self.create_tile(model_name="device_type", changelist_url="admin:core_devicetype_changelist"),
            self.create_tile(model_name="room", changelist_url="admin:core_room_changelist"),
        ]

        context.update(dict(
            record_fraction_data=json.dumps(stats.get_record_fraction_data()),
            device_type_data=json.dumps(stats.get_device_type_data()),
            current_inventory=Inventory.objects.filter(is_active=True).order_by('-created_at').first(),
            device_count=Device.objects.all().count(),
            notebooks_lending_data=json.dumps(stats.get_notebooks_lending_data()),
            custom_buttons=custom_buttons,
            tiles=tiles,
        ))
        return context
