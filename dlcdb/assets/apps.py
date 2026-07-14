# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.assets"
    verbose_name = _("Assets")

    def ready(self):
        # Register the relocate device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()
