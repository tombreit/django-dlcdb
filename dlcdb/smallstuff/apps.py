# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SmallstuffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.smallstuff"
    verbose_name = _("Smallstuff")

    nav_entries = [
        {
            "slot": "nav_main",
            "order": 30,
            "label": _("Smallstuff"),
            "icon": "bi bi-handbag",
            "url": "smallstuff:person_search",
            "required_permission": "view_assignedthing",
        },
    ]
