# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_settings",
        "order": 10,
        "label": _("Branding"),
        "icon": "bi bi-palette",
        "url": "admin:organization_branding_changelist",
        "required_permission": "view_branding",
    },
]
