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
            "order": 6,
            "label": "Licenses",
            "icon": "fa-solid fa-glasses",
            "url": "licenses:index",
            "required_permission": "true",
        },
    ]
