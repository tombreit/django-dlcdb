# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    readonly_fields = (
        "title",
        "body",
        "spreadsheet",
    )

    def has_add_permission(self, request):
        return False
