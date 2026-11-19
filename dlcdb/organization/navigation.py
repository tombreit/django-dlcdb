# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 10,
        "label": _("Organization"),
        "icon": "bi bi-building",
        "url": "organization:branding",
        "required_permission": "organization.view_branding",
    },
]
