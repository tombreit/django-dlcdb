# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DataexchangeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.dataexchange"
    verbose_name = _("Data exchange")

    nav_entries = [
        {
            "slot": "nav_processes",
            "order": 20,
            "label": _("Bulk Import"),
            "icon": "",
            "url": "admin:dataexchange_importerlist_changelist",
            "required_permission": "view_importerlist",
        },
        {
            "slot": "nav_processes",
            "order": 30,
            "label": _("Bulk Decommissioning"),
            "icon": "",
            "url": "admin:dataexchange_removerlist_changelist",
            "required_permission": "view_removerlist",
        },
    ]
