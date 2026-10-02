# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 50,
        "label": _("Journal"),
        "icon": "bi bi-journal-text",
        "url": "journal:index",
        "required_permission": "journal.view_journalentry",
    },
]
