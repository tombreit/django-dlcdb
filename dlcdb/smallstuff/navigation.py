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
    {
        "slot": "nav_settings",
        "order": 40,
        "label": _("Smallstuff catalogue"),
        "group": "modules",
        "description": _("The things that can be handed out to persons"),
        "search_terms": _("things, webcams, mice, accessories"),
        "icon": "bi bi-handbag",
        "url": "smallstuff:thing:index",
        "required_permission": "smallstuff.view_thing",
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
