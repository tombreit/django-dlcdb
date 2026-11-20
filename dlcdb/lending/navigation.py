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
        "search_terms": _("mails, notifications, slip template, print, preparation checklist, device types, borrower"),
        "icon": "bi bi-arrow-left-right",
        "url": "lending:configuration",
        "required_permission": "lending.view_lendingconfiguration",
        # The lending profiles are listed on the configuration page.
        "active_url_names": {"configuration", "profile_add", "profile_detail", "profile_history", "profile_delete"},
    },
    {
        # core.Link: the documents a lending profile asks the borrower to confirm.
        "slot": "nav_settings",
        "order": 25,
        "label": _("Lending regulations"),
        "group": "modules",
        "description": _("The regulations the lending profiles ask borrowers to confirm, as link or file"),
        "search_terms": _("links, documents, PDF, terms of use"),
        "icon": "bi bi-file-earmark-text",
        "url": "admin:core_link_changelist",
        "required_permission": "core.view_link",
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
