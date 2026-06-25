# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from ..models import DeviceType
from ..utils.helpers import get_has_note_badge
from dlcdb.theme.widgets import IconPickerWidget
from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin, DeviceCountMixin
from .filters.has_note_filter import HasNoteFilter


@admin.register(DeviceType)
class DeviceTypeAdmin(DeviceCountMixin, SoftDeleteModelAdmin, CustomBaseModelAdmin):
    list_display = (
        "name",
        "prefix",
        "icon",
        "has_note",
    ) + CustomBaseModelAdmin.list_display

    list_filter = (HasNoteFilter,)

    search_fields = (
        "name",
        "prefix",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "prefix",
                    "icon",
                    "note",
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
                    (
                        "deleted_at",
                        "deleted_by",
                    ),
                ),
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "icon":
            kwargs["widget"] = IconPickerWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="Has Note?")
    def has_note(self, obj):
        return get_has_note_badge(obj_type="core.devicetype", has_note=obj.note)
