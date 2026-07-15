# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


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
        "required_permission": "licenses.view_licensesconfiguration",
    },
]

nav_focus = {
    "navbar_secondary": [
        {
            "label": _("Docs"),
            "href": "/docs/guides/lizenzen.html",
            "icon": "bi bi-book",
        },
    ],
}
