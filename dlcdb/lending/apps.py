# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LendingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.lending"

    def ready(self):
        # Register the lending device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()

    nav_entries = [
        {
            "slot": "nav_settings",
            "order": 20,
            "label": _("Lending configuration"),
            "icon": "bi bi-arrow-left-right",
            "url": "admin:lending_lendingconfiguration_changelist",
            "required_permission": "view_lendingconfiguration",
        },
        {
            "slot": "nav_settings",
            "order": 25,
            "label": _("Lending profiles"),
            "icon": "bi bi-card-checklist",
            "url": "admin:lending_lendingprofile_changelist",
            "required_permission": "view_lendingprofile",
        },
    ]
