# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json

from django.urls import path
from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.contrib.admin.models import LogEntry
from django.contrib import messages
from django.shortcuts import redirect

from .models import Notification, Report
from .utils.email import build_report_email, send_email
from .utils.process import create_report_if_needed

admin.site.register(LogEntry)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "trigger-report/<int:notification_pk>",
                self.admin_site.admin_view(self.trigger_oneshot_reporting),
                name="trigger-report",
            )
        ]
        all_urls = custom_urls + urls
        return all_urls

    def trigger_oneshot_reporting(self, request, notification_pk):
        Result = create_report_if_needed(notification_pk, caller="oneshot")
        notification_obj = Notification.objects.get(pk=notification_pk)

        try:
            email_objs = build_report_email(notification_obj, Result.report, Result.record_collection)
            send_email(email_objs)
            messages.info(request, "Report wurde per Email versendet.")
        except BaseException as e:
            messages.warning(request, f"Kein Report versendet: {e}")

        # TODO: redirect to change view does not refresh from db?
        redirect_to = redirect("admin:reporting_notification_change", notification_pk)
        # redirect_to = redirect('admin:reporting_notification_changelist')
        return redirect_to


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    readonly_fields = (
        "notification",
        "title",
        "body",
        "spreadsheet",
    )

    def changelist_view(self, request, extra_context=None):
        from ..core.models import Record

        _records = (
            Record.objects
            # .filter(created_at__year__gte='2019')
        )

        chart_data_lent = (
            _records.filter(record_type=Record.LENT)
            .annotate(date=TruncMonth("created_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )

        chart_data_removed = (
            _records.filter(record_type=Record.REMOVED)
            .annotate(date=TruncMonth("created_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )

        chart_data_inroom = (
            _records.filter(record_type=Record.INROOM)
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
