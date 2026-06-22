# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OrganizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.organization"

    nav_entries = [
        {
            "slot": "nav_settings",
            "order": 10,
            "label": _("Branding"),
            "icon": "fa-solid fa-palette",
            "url": "admin:organization_branding_changelist",
            "required_permission": "view_branding",
        },
    ]
