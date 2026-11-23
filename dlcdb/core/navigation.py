# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

# Rooms, Manufacturer, Distributor, Device types, People and Records are owned
# by their frontend apps (dlcdb.rooms, dlcdb.assets, dlcdb.persons
# navigation.py); core only keeps the admin-changelist entries that have no
# frontend yet, in Master data and on the Settings page. Inventories are under
# Settings too (dlcdb.inventory).
nav_entries = [
    {
        "slot": "nav_masterdata",
        "order": 90,
        "label": _("Notes"),
        "icon": "bi bi-chat",
        "url": "admin:core_note_changelist",
        "required_permission": "core.view_note",
    },
    {
        "slot": "nav_settings",
        "order": 70,
        "label": _("Record attachments"),
        "group": "data",
        "description": _("Files attached to records, with their titles"),
        "search_terms": _("invoices, delivery notes, files, uploads, documents"),
        "icon": "bi bi-paperclip",
        "url": "admin:core_attachment_changelist",
        "required_permission": "core.view_attachment",
    },
    {
        "slot": "nav_settings",
        "order": 60,
        "label": _("Admin history"),
        "group": "logs",
        "description": _("Changes made in the Django admin, and entries the HR sync writes there"),
        "search_terms": _("log entries, audit, who changed, edits"),
        "icon": "bi bi-list-check",
        "url": "admin:admin_logentry_changelist",
        "required_permission": "admin.view_logentry",
    },
]
