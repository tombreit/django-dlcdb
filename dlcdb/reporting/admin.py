import json

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth
from django.contrib.admin.models import LogEntry

from .models import Notification, Report


admin.site.register(LogEntry)
admin.site.register(Notification)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    readonly_fields = (
        'notification',
        'title',
        'body',
        'spreadsheet', 
    )

    def changelist_view(self, request, extra_context=None):
        from ..core.models import Record
        # Aggregate new subscribers per day

        _records = (
            Record
            .objects
            # .filter(created_at__year__gte='2019')
        )

        chart_data_lent = (
            _records
            .filter(record_type=Record.LENT)
            .annotate(date=TruncMonth("created_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )

        chart_data_removed = (
            _records
            .filter(record_type=Record.REMOVED)
            .annotate(date=TruncMonth("created_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )

        chart_data_inroom = (
            _records
            .filter(record_type=Record.INROOM)
            .annotate(date=TruncMonth("created_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )

        # Serialize and attach the chart data to the template context
        as_json_lent = json.dumps(list(chart_data_lent), cls=DjangoJSONEncoder)
        as_json_removed = json.dumps(list(chart_data_removed), cls=DjangoJSONEncoder)
        as_json_inroom = json.dumps(list(chart_data_inroom), cls=DjangoJSONEncoder)

        extra_context = extra_context or {
            "chart_data_lent": as_json_lent,
            "chart_data_removed": as_json_removed,
            "chart_data_inroom": as_json_inroom,
        }

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)

