# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.urls import path
from django.shortcuts import render, get_object_or_404
from django.utils.html import format_html

from simple_history.admin import SimpleHistoryAdmin

from .models import Subscription, Message


@admin.register(Subscription)
class SubscriptionAdmin(SimpleHistoryAdmin):
    list_display = [
        "id",
        "event",
        "device",
        "interval",
        "next_scheduled",
        "subscriber",
        "subscribed_at",
        "is_active",
    ]
    list_filter = [
        "event",
        "interval",
        "subscribed_at",
        "is_active",
    ]

    show_facets = admin.ShowFacets.NEVER


@admin.register(Message)
class MessageAdmin(SimpleHistoryAdmin):
    list_display = [
        "id",
        "subscription",
        "preview_link",  # Add this new column
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

    def preview_link(self, obj):
        """Add a link to preview the message"""
        return format_html('<a href="{}">Preview</a>', f"preview/{obj.pk}/")

    preview_link.short_description = "Preview"

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
        """Custom view to preview message content"""
        message = get_object_or_404(Message, pk=message_id)

        # Get the message content - adjust this based on your actual implementation
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
