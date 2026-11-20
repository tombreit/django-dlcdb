# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_masterdata",
        "order": 10,
        "label": _("Rooms"),
        "icon": "bi bi-door-open",
        "url": "rooms:index",
        "required_permission": "core.view_room",
    },
    {
        "slot": "nav_settings",
        "order": 10,
        "label": _("Room reconcile"),
        "group": "data",
        "description": _("Compare the rooms with an Archibus CSV export"),
        "search_terms": _("Archibus, CSV, upload, compare"),
        "icon": "bi bi-file-earmark-arrow-up",
        "url": "admin:core_roomreconcile_changelist",
        "required_permission": "core.view_roomreconcile",
    },
]
