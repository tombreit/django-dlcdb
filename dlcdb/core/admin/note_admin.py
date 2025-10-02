# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from ..models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = [
        "text",
        "device",
        "device__sap_id",
        "get_device_room",
        "inventory",
        "room",
        "updated_at",
    ]
    list_filter = [
        "inventory",
        # TODO: Filter got same filter title as the next filter: room
        # "device__active_record__room",
        "device",
        "room",
        "updated_at",
    ]
    search_fields = [
        "text",
        "device__edv_id",
        "device__sap_id",
        "room__number",
        "room__nickname",
    ]
    readonly_fields = [
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ]

    show_facets = admin.ShowFacets.NEVER

    @admin.display(description="Device room")
    @admin.display(ordering="device__active_record__room")
    def get_device_room(self, obj):
        if hasattr(obj, "device") and obj.device:
            return obj.device.active_record.room

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        # Use the current items of search_fields as they are
        fields = [str(f) for f in self.search_fields]
        extra_context.setdefault(
            "search_help",
            f"Searches: {', '.join(fields)}.",
        )
        return super().changelist_view(request, extra_context=extra_context)
