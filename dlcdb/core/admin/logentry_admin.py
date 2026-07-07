# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.contrib.admin.models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """
    Expose Django's admin log in the admin, read-only. Besides admin edits it
    contains entries written programmatically, e.g. by the UDB sync
    (dlcdb.dataexchange).
    """

    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_repr",
        "action_flag",
        "change_message",
    ]
    list_filter = [
        "action_flag",
        "content_type",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
