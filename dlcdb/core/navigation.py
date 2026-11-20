# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

# Rooms, Manufacturer, Distributor, Device types, People and Records are owned
# by their frontend apps (dlcdb.rooms, dlcdb.assets, dlcdb.persons
# navigation.py); core only keeps the admin-changelist entries that have no
# frontend yet. Inventories are under Settings (dlcdb.inventory).
nav_entries = [
    {
        "slot": "nav_masterdata",
        "order": 70,
        "label": _("Removed records"),
        "icon": "bi bi-stack",
        "url": "admin:core_removedrecord_changelist",
        "required_permission": "core.view_record",
    },
    {
        "slot": "nav_masterdata",
        "order": 90,
        "label": _("Notes"),
        "icon": "bi bi-chat",
        "url": "admin:core_note_changelist",
        "required_permission": "core.view_note",
    },
]
