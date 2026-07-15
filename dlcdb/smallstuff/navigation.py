# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_main",
        "order": 30,
        "label": _("Smallstuff"),
        "icon": "bi bi-handbag",
        "url": "smallstuff:person_search",
        "required_permission": "smallstuff.view_assignedthing",
    },
]

nav_focus = {
    "navbar_secondary": [
        {
            "label": _("Docs"),
            "href": "/docs/guides/kleinkram.html",
            "icon": "bi bi-book",
        },
    ],
}
