# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from .models import LicensesConfiguration


@admin.register(LicensesConfiguration)
class LicensesConfigurationAdmin(admin.ModelAdmin):
    autocomplete_fields = [
        "default_subscribers",
    ]
