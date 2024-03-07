# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from ..utils.helpers import get_has_note_badge
from ..models import Manufacturer
from .base_admin import DeviceCountMixin


@admin.register(Manufacturer)
class ManufacturerAdmin(DeviceCountMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "has_note",
    ]
    search_fields = [
        "name",
        "note",
    ]

    @admin.display(description="Has Note?")
    def has_note(self, obj):
        return get_has_note_badge(obj_type="core.manufacturer", has_note=obj.note)
