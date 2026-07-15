# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_main",
        "order": 5,
        "label": _("Lending"),
        "icon": "bi bi-arrow-left-right",
        "url": "lending:index",
        "required_permission": "view_lentrecord",
    },
    {
        "slot": "nav_settings",
        "order": 20,
        "label": _("Lending configuration"),
        "icon": "bi bi-arrow-left-right",
        "url": "admin:lending_lendingconfiguration_changelist",
        "required_permission": "view_lendingconfiguration",
    },
    {
        "slot": "nav_settings",
        "order": 25,
        "label": _("Lending profiles"),
        "icon": "bi bi-card-checklist",
        "url": "admin:lending_lendingprofile_changelist",
        "required_permission": "view_lendingprofile",
    },
]

nav_focus = {
    "navbar_secondary": [
        {
            "label": _("Docs"),
            "href": "/docs/guides/ausleihe.html",
            "icon": "bi bi-book",
        },
    ],
}
