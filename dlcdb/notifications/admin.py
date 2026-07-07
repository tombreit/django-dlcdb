# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html

from simple_history.admin import SimpleHistoryAdmin

from .models import Subscription, Message
from .reports import create_report_message
from .tasks import send_message


@admin.register(Subscription)
class SubscriptionAdmin(SimpleHistoryAdmin):
    list_display = [
        "id",
        "event",
        "condition",
        "device",
        "interval",
        "next_scheduled",
        "last_run",
        "subscriber",
        "is_active",
    ]
    list_filter = [
        "event",
        "condition",
        "interval",
        "is_active",
    ]

    show_facets = admin.ShowFacets.NEVER

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "trigger-report/<int:pk>",
                self.admin_site.admin_view(self.trigger_adhoc_report),
                name="notifications_subscription_trigger",
            ),
        ]
        return custom_urls + urls

    def trigger_adhoc_report(self, request, pk):
        """Create and immediately send a report, without shifting the reporting window."""
        subscription = get_object_or_404(Subscription, pk=pk)

        if not subscription.is_report_subscription:
            messages.warning(request, "Ad hoc reports are only available for report subscriptions.")
            return redirect("admin:notifications_subscription_change", pk)

        message = create_report_message(subscription, update_window=False)
        if message and send_message.call_local(message.id):
            messages.info(request, "Report has been sent via email.")
        else:
            messages.warning(request, "No report sent.")

        return redirect("admin:notifications_subscription_change", pk)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "subscription",
        "recipient_email",
        "preview_link",
        "sent_at",
        "status",
        "created_at",
        "modified_at",
    ]
    list_filter = [
        "status",
        "subscription__event",
        "subscription__subscriber",
        "created_at",
        "modified_at",
    ]

    show_facets = admin.ShowFacets.NEVER

    @admin.display(description="Preview")
    def preview_link(self, obj):
        """Add a link to preview the message"""
        return format_html('<a href="{}">Preview</a>', f"preview/{obj.pk}/")

    def get_urls(self):
        """Add custom URL patterns for the admin"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "preview/<int:message_id>/",
                self.admin_site.admin_view(self.message_preview_view),
                name="notifications_message_preview",
            ),
        ]
        return custom_urls + urls

    def message_preview_view(self, request, message_id):
        """Custom view to preview message content and send it ad hoc"""
        message = get_object_or_404(Message, pk=message_id)

        if request.method == "POST" and "_send_now" in request.POST:
            if send_message.call_local(message.pk):
                messages.info(request, f"Message {message.pk} has been sent.")
            else:
                messages.warning(request, f"Message {message.pk} could not be sent, see its error message.")
            return redirect("admin:notifications_message_change", message.pk)

        subject, body = message.get_content()

        context = {
            "opts": self.model._meta,
            "title": f"Preview Message #{message.pk}",
            "message": message,
            "subject": subject,
            "body": body,
            "app_label": self.model._meta.app_label,
            "original": message,
            "has_change_permission": self.has_change_permission(request, message),
        }

        return render(request, "notifications/message/preview.html", context)
