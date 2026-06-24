# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LicensesConfig(AppConfig):
    name = "dlcdb.licenses"
    verbose_name = _("License Management")

    nav_entries = [
        {
            "slot": "nav_main",
            "order": 40,
            "label": _("Licenses"),
            "icon": "bi bi-bank2",
            "url": "licenses:index",
            "required_permission": "true",
        },
        {
            "slot": "nav_settings",
            "order": 30,
            "label": _("Licenses configuration"),
            "icon": "bi bi-bank2",
            "url": "admin:licenses_licensesconfiguration_changelist",
            "required_permission": "view_licensesconfiguration",
        },
    ]
