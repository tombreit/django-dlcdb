# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from ..models import Supplier
from .base_admin import DeviceCountMixin, get_has_note_badge


@admin.register(Supplier)
class SupplierAdmin(DeviceCountMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "contact",
        "has_note",
    ]
    search_fields = [
        "name",
        "note",
    ]

    @admin.display(description="Has Note?")
    def has_note(self, obj):
        return get_has_note_badge(obj_type="core.supplier", has_note=obj.note)
