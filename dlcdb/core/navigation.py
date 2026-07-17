# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


# Rooms, Manufacturer, Distributor, Device types and People are owned by their
# frontend apps (dlcdb.rooms, dlcdb.assets, dlcdb.persons navigation.py); core
# only keeps the admin-changelist entries that have no frontend yet.
nav_entries = [
    {
        "slot": "nav_masterdata",
        "order": 60,
        "label": _("Records"),
        "icon": "bi bi-stack",
        "url": "admin:core_record_changelist",
        "required_permission": "core.view_record",
    },
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
        "order": 80,
        "label": _("Inventories"),
        "icon": "bi bi-eyeglasses",
        "url": "admin:core_inventory_changelist",
        "required_permission": "core.change_inventory",
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
