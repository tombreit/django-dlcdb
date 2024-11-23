# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig


class SmallstuffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.smallstuff"

    nav_entries = [
        {
            "slot": "nav_main",
            "order": 30,
            "label": "Kleinkram",
            "icon": "bi bi-handbag",
            "url": "smallstuff:person_search",
            "required_permission": "view_assignedthing",
        },
        # ... additional entries as needed
    ]
