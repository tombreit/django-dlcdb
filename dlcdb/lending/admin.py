# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from simple_history.admin import SimpleHistoryAdmin
from simple_history.template_utils import HistoricalRecordContextHelper

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
    fieldsets = (
        (None, {"fields": ("admin_mark_overdue",)}),
        (
            "Overdue lender notifications",
            {"fields": ("overdue_notifications_recipient",)},
        ),
    )

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


class LendingProfileHistoryContextHelper(HistoricalRecordContextHelper):
    """
    Render the long TextFields in full in the admin history "Changes" column,
    instead of the 100 character shortened diff, so a previous version can be
    read and copied back into the change form.
    """

    long_text_fields = frozenset({"lent_sheet_template", "lending_preparation_checklist"})

    def stringify_delta_change_values(self, change, old, new):
        # `change.field` is still the raw field name here; `format_delta_change()`
        # only swaps in the verbose name afterwards.
        if change.field not in self.long_text_fields:
            return super().stringify_delta_change_values(change, old, new)

        return tuple(
            mark_safe(  # noqa: S308 - the value itself is escaped by the template
                render_to_string(
                    "lending/admin/history_value.html",
                    {
                        "label": label,
                        "value": value,
                        # Fit the textarea to the value, within reason.
                        "rows": min(25, max(2, str(value).count("\n") + 2)),
                    },
                )
            )
            for label, value in (("Before", old), ("After", new))
        )


@admin.register(LendingProfile)
class LendingProfileAdmin(SimpleHistoryAdmin):
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

    # django-simple-history
    # https://django-simple-history.readthedocs.io/en/latest/admin.html
    # Reverting is disabled globally via SIMPLE_HISTORY_REVERT_DISABLED.
    object_history_template = "lending/admin/object_history.html"

    def get_historical_record_context_helper(self, request, historical_record):
        return LendingProfileHistoryContextHelper(self.model, historical_record)

    class Media:
        css = {"all": ("lending/admin/lending_admin.css",)}
