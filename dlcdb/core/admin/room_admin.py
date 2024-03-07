# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.utils.html import mark_safe
from django.utils.html import format_html
from django.urls import reverse

from ..models import Room
from ..models.room import RoomReconcile
from ..utils.helpers import get_has_note_badge
from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin
from .filters.has_note_filter import HasNoteFilter
from .base_admin import DeviceCountMixin


@admin.register(Room)
class RoomAdmin(DeviceCountMixin, SoftDeleteModelAdmin, CustomBaseModelAdmin):
    change_list_template = "core/room/change_list.html"

    ordering = ["number"]

    list_display = (
        "number",
        "nickname",
        "description",
        "website_link",
        "has_note",
        "is_auto_return_room",
        "is_external",
        "deleted_at",
    )  # + CustomBaseModelAdmin.list_display

    list_filter = [
        "is_auto_return_room",
        "is_external",
        HasNoteFilter,
    ]
    search_fields = [
        "number",
        "nickname",
        # 'uuid',
    ]
    # exclude = ['qrcode']
    readonly_fields = [
        "uuid",
        "qrcode_display",
        # 'qrcode',
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "number",
                    "nickname",
                    "description",
                    "website",
                    "note",
                    "is_auto_return_room",
                    "is_external",
                )
            },
        ),
        (
            "Informal",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "modified_at",
                    "user",
                    "username",
                    "uuid",
                    "qrcode_display",
                    # 'qrcode',
                    (
                        "deleted_at",
                        "deleted_by",
                    ),
                ),
            },
        ),
    )

    @admin.display(description="QR Code")
    def qrcode_display(self, obj):
        return mark_safe(
            '<img src="{url}" width="{width}" height="{height}">'.format(
                url=obj.qrcode.url,
                width=200,
                height=200,
            )
        )

    @admin.display(description="Has Note?")
    def has_note(self, obj):
        return get_has_note_badge(obj_type="core.room", has_note=obj.note)

    @admin.display(description="Website")
    def website_link(self, obj):
        if obj.website:
            return mark_safe(
                '<a href="{url}"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>'.format(
                    url=obj.website,
                )
            )

    # Falling back to our no-delete-permission via CustomBaseModelAdmin
    # def has_delete_permission(self, request, obj=None):
    #     return True


@admin.register(RoomReconcile)
class RoomReconcileAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "file",
        "note",
        "get_reconcile_button",
    ]

    @admin.display(description="Abgleich")
    def get_reconcile_button(self, obj):
        return format_html(
            '<a class="btn btn-warning" href="{}">&rarr; {}</a>',
            reverse("core:reconcile-rooms", args=[obj.id]),
            "Abgleichen",
        )
