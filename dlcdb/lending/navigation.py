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
        "required_permission": "core.view_lentrecord",
        "active_url_names": {"index", "lend", "detail", "person_search"},
    },
    {
        "slot": "nav_settings",
        "order": 20,
        "label": _("Lending configuration"),
        "icon": "bi bi-arrow-left-right",
        "url": "lending:configuration",
        "required_permission": "lending.view_lendingconfiguration",
        "active_url_names": {"configuration"},
    },
    {
        "slot": "nav_settings",
        "order": 25,
        "label": _("Lending profiles"),
        "icon": "bi bi-card-checklist",
        "url": "admin:lending_lendingprofile_changelist",
        "required_permission": "lending.view_lendingprofile",
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
