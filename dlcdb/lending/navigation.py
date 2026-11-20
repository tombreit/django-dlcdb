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
        "group": "modules",
        "description": _("Overdue reminders; the lending profiles with their slips and regulations"),
        "icon": "bi bi-arrow-left-right",
        "url": "lending:configuration",
        "required_permission": "lending.view_lendingconfiguration",
        # The lending profiles are listed on the configuration page.
        "active_url_names": {"configuration", "profile_add", "profile_detail", "profile_history", "profile_delete"},
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
