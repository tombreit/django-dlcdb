# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig


class LendingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.lending"

    def ready(self):
        # Register the lending device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()
