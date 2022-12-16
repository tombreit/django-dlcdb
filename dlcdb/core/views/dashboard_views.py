import json

from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from ..utils.helpers import get_has_note_badge
from ..models.inventory import Inventory
from ..models import Device, Room, DeviceType

from dlcdb.core import stats


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        button_template = 'admin/dashboard_button.html'

        rooms_with_notes_count = Room.objects.exclude(note__exact="").count()
        room_button_context = {
            "css_classes": "btn btn-warning btn-lg",
            # WARNING: Do not use the key name "url" as this triggers a
            # circular import. And please don't ask why...
            "url": reverse_lazy('admin:core_room_changelist'),
            "query_params": "has_note=has_note",
            "badge": get_has_note_badge(obj_type="room", has_note=rooms_with_notes_count),
            "text": f"{rooms_with_notes_count} Room with notes",
        }
        rendered_room_button = render_to_string(button_template, room_button_context)

        device_types_with_notes_count = DeviceType.objects.exclude(note__exact="").count()
        device_type_button_context = {
            "css_classes": "btn btn-warning btn-lg",
            # WARNING: Do not use the key name "url" as this triggers a
            # circular import. And please don't ask why...
            "url": reverse_lazy('admin:core_devicetype_changelist'),
            "query_params": "has_note=has_note",
            "badge": get_has_note_badge(obj_type="device_type", has_note=rooms_with_notes_count),
            "text": f"{device_types_with_notes_count} DeviceTypes with notes",
        }
        rendered_device_type_button = render_to_string(button_template, device_type_button_context)

        custom_buttons = [
            rendered_room_button,
            rendered_device_type_button,
        ]

        context.update(dict(
            record_fraction_data=json.dumps(stats.get_record_fraction_data()),
            device_type_data=json.dumps(stats.get_device_type_data()),
            current_inventory=Inventory.objects.filter(is_active=True).order_by('-created_at').first(),
            device_count=Device.objects.all().count(),
            notebooks_lending_data=json.dumps(stats.get_notebooks_lending_data()),
            custom_buttons=custom_buttons,
        ))
        return context
