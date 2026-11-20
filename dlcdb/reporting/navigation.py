# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 60,
        "label": _("Reports"),
        "group": "modules",
        "description": _("Generated reports with their spreadsheets, sent by the notifications"),
        "search_terms": _("xlsx, excel, spreadsheet, mails"),
        "icon": "bi bi-file-earmark-spreadsheet",
        "url": "admin:reporting_report_changelist",
        "required_permission": "reporting.view_report",
    },
]
