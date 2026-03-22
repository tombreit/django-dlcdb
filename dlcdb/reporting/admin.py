# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path
from django.contrib import admin
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
