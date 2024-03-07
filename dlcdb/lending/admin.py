# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.db import models
from django.forms import Textarea

from .models import LendingConfiguration, LendingConfigurationRegulation


class RegulationInline(admin.TabularInline):
    model = LendingConfigurationRegulation
    extra = 1


@admin.register(LendingConfiguration)
class LendingConfigurationAdmin(admin.ModelAdmin):
    search_fields = [
        "lending_preparation_checklist",
    ]

    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"style": "width: 100%;"})},
    }

    fieldsets = (
        (
            "Printouts",
            {
                # 'classes': ('collapse',),
                "fields": ("lending_preparation_checklist",),
            },
        ),
        # (
        #     "Regulations",
        #     {
        #         "classes": ("collapse",),
        #         "fields": ("mandatory_regulations",),
        #     },
        # ),
    )

    inlines = [
        RegulationInline,
    ]
    exclude = ["mandatory_regulations"]

    def has_add_permission(self, request):
        return not LendingConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        False

    class Media:
        css = {"all": ("lending/admin/lending_admin.css",)}
