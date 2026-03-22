# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.db import models
from django.forms import Textarea

from .models import (
    LendingConfiguration,
    LendingConfigurationRegulation,
    LendingProfile,
    LendingProfileRegulation,
)


class RegulationInline(admin.TabularInline):
    model = LendingConfigurationRegulation
    extra = 1


@admin.register(LendingConfiguration)
class LendingConfigurationAdmin(admin.ModelAdmin):
    fieldsets = ((None, {"fields": ("admin_mark_overdue",)}),)

    inlines = [
        RegulationInline,
    ]
    exclude = ["mandatory_regulations", "lending_preparation_checklist"]

    def has_add_permission(self, request):
        return not LendingConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("lending/admin/lending_admin.css",)}


class ProfileRegulationInline(admin.TabularInline):
    model = LendingProfileRegulation
    extra = 1


@admin.register(LendingProfile)
class LendingProfileAdmin(admin.ModelAdmin):
    list_display = ["device_type", "has_template", "has_checklist"]
    list_select_related = ["device_type"]
    search_fields = ["device_type__name"]

    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"style": "width: 100%; font-family: monospace;", "rows": 30})},
    }

    fieldsets = (
        (None, {"fields": ("device_type",)}),
        (
            "Lent Sheet Template",
            {
                "fields": ("lent_sheet_template",),
                "description": (
                    "Django template syntax (HTML). "
                    "Should extend 'lending/printout_base.html'. "
                    "Available context: record, lending_profile, sheet_for, pagebreak."
                ),
            },
        ),
        (
            "Preparation Checklist",
            {
                "fields": ("lending_preparation_checklist",),
            },
        ),
    )

    inlines = [ProfileRegulationInline]
    exclude = ["mandatory_regulations"]

    @admin.display(boolean=True, description="Has template")
    def has_template(self, obj):
        return bool(obj.lent_sheet_template)

    @admin.display(boolean=True, description="Has checklist")
    def has_checklist(self, obj):
        return bool(obj.lending_preparation_checklist)

    class Media:
        css = {"all": ("lending/admin/lending_admin.css",)}
