import json

from django.urls import path
from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncMonth
from django.contrib.admin.models import LogEntry
from django.shortcuts import redirect

from .models import Notification, Report


admin.site.register(LogEntry)
from .utils.email import build_report_email, send_email
from .utils.process import create_report_if_needed

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    save_on_top = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'trigger-report/<int:notification_pk>',
                self.admin_site.admin_view(self.trigger_oneshot_reporting),
                name="trigger-report",
            )
        ]
        all_urls = custom_urls + urls
        return all_urls

    def trigger_oneshot_reporting(self, request, notification_pk):
        print("trigger_oneshot_reporting...")

        Result = create_report_if_needed(notification_pk, caller='oneshot')
        
        notification_obj = Notification.objects.get(pk=notification_pk)
        if notification_obj.active:
            if notification_obj.notify_no_updates or hasattr(Result, 'record_collection.records'):
                email_objs = build_report_email(notification_obj, Result.report, Result.record_collection)
                send_email(email_objs)

        # TODO: trigger message

        return redirect('admin:reporting_notification_change', notification_pk)


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

