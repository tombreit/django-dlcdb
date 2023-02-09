import json
from collections import defaultdict
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.apps import apps
from django.utils.text import slugify
from django.http import JsonResponse

from ..utils.helpers import get_has_note_badge, get_icon_for_class
from .. import stats


def get_chartjs_data(request, record_type_name):
    model_class_name = record_type_name
    ModelClass = apps.get_model(model_class_name)

    def _populate_date_range(earliest_datetime, latest_datetime):
        date_keys_dict = defaultdict(set)

        earliest_year = int(f"{earliest_datetime:%Y}")
        earliest_month = int(f"{earliest_datetime:%m}")

        latest_year = int(f"{latest_datetime:%Y}")
        latest_month = int(f"{latest_datetime:%m}")

        for year in range(earliest_year, latest_year+1):
            if year == earliest_year:
                for month in range(earliest_month, 13):
                    date_keys_dict[f"{year}-{month}"]
            elif year == latest_year:
                for month in range(1, latest_month+1):
                    date_keys_dict[f"{year}-{month}"]
            else:
                for month in range(1, 13):
                    date_keys_dict[f"{year}-{month}"]

        return date_keys_dict

    qs = ModelClass.objects.order_by("created_at")

    if qs:
        earliest = qs.earliest("created_at")
        latest = qs.latest("created_at")
        date_keys_dict = _populate_date_range(earliest.created_at, latest.created_at)

        for record in qs:
            valid_from_to = _populate_date_range(record.created_at, record.effective_until if record.effective_until else latest.created_at)
            valid_from_to = list(valid_from_to.keys())

            for valid_datestamp in valid_from_to:
                devices = date_keys_dict.get(valid_datestamp, set())
                devices.add(record.device)
                date_keys_dict[valid_datestamp] = devices

        # chart.js expected data property:
        # data: [{x: 10, y: 20}, {x: 15, y: null}, {x: 20, y: 10}]

        data = []
        for date, devices in date_keys_dict.items():
            data.append({
                "x": date,
                "y": len(devices),
            })
    else:
        data = None

    # return json.dumps(data, cls=DjangoJSONEncoder)
    return JsonResponse(data, safe=False)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'admin/dashboard.html'

    @staticmethod
    def create_tile(*, model_name, url, chart_data_url=None):
        from ..models import Record

        model_class_name = model_name
        ModelClass = apps.get_model(model_class_name)

        obj_notes_count = None
        obj_count = ModelClass.objects.all().count()
        human_model_name = ModelClass._meta.verbose_name_plural if obj_count >=2 else ModelClass._meta.verbose_name
        model_class_icon = get_icon_for_class(model_name)

        if hasattr(ModelClass, "note"):
            obj_notes_count = ModelClass.objects.exclude(note__exact="").count()
            obj_notes_count = obj_notes_count if obj_notes_count >= 1 else ""

        if model_name == "core.lentrecord":
            lented_count = ModelClass.objects.filter(record_type=Record.LENT).count()
            obj_count = f"{lented_count} / {obj_count}"
        elif model_name == "core.inventory":
            obj_count = ModelClass.objects.filter(is_active=True).first()

        template = 'admin/dashboard_tile.html'
        context = {
            "css_classes": "btn btn-lg btn-{}".format("warning" if obj_notes_count else "primary"),
            "url": reverse_lazy(url),
            "query_params": "has_note=has_note" if obj_notes_count else "",
            "text": human_model_name,
            "hover_text": f"{obj_notes_count} {human_model_name} with notes" if obj_notes_count else "",
            "obj_count": obj_count,
            "model_class_icon": model_class_icon,
            "model_name_slug": slugify(model_name),
            "chart_data_url": chart_data_url,
        }

        if not any([
            model_name == "core.device",
            model_name == "core.lentrecord",
            model_name == "core.licencerecord",
        ]):
            context.update({
                "badge": get_has_note_badge(obj_type=model_name, has_note=obj_notes_count) if obj_notes_count else "",
            })

        return render_to_string(template, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tiles = [
            self.create_tile(model_name="core.device", url="admin:core_device_changelist"),
            self.create_tile(model_name="core.lentrecord", url="admin:core_lentrecord_changelist"),
            self.create_tile(model_name="core.room", url="admin:core_room_changelist"),
            self.create_tile(model_name="core.devicetype", url="admin:core_devicetype_changelist"),
            self.create_tile(model_name="core.licencerecord", url="admin:core_licencerecord_changelist"),
            self.create_tile(model_name="smallstuff.assignedthing", url="smallstuff:person_search"),
            self.create_tile(model_name="core.inventory", url="inventory:inventorize-room-list"),
            self.create_tile(
                model_name="core.lostrecord",
                url="admin:core_lostrecord_changelist",
                chart_data_url=reverse_lazy("core:get_chartjs_data", args=["core.lostrecord"]),
            ),
        ]

        context.update(dict(
            record_fraction_data=json.dumps(stats.get_record_fraction_data()),
            device_type_data=json.dumps(stats.get_device_type_data()),
            tiles=tiles,
        ))
        return context
