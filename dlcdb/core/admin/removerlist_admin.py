# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from ..models import RemoverList


@admin.register(RemoverList)
class RemoverListAdmin(admin.ModelAdmin):
    fields = (
        "file",
        "note",
        "messages",
        "created_at",
        "modified_at",
    )

    readonly_fields = (
        "messages",
        "created_at",
        "modified_at",
    )

    list_display = [
        "get_change_link_display",
        "created_at",
        "modified_at",
        "note",
    ]

    def get_change_link_display(self, obj):
        return "{label}".format(label=obj.file)

    get_change_link_display.short_description = "CSV-Datei"
