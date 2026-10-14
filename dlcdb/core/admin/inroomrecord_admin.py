# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from dlcdb.tenants.admin import TenantScopedRecordAdmin

from ..models import InRoomRecord
from .base_admin import CustomBaseProxyModelAdmin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(TenantScopedRecordAdmin, CustomBaseProxyModelAdmin):
    list_display = [
        "device",
        "created_at",
        "note",
    ]

    fields = [
        "device",
        "room",
        "note",
    ]

    autocomplete_fields = [
        "room",
    ]

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        """Hides the extra save buttons."""
        context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
                "show_activate_deactivate": False,
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)
