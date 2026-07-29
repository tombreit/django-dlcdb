# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LendingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.lending"
    verbose_name = _("Lending")

    def ready(self):
        # Register the lending device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()
