# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InventoryConfig(AppConfig):
    name = "dlcdb.inventory"
    verbose_name = "DLCDB Inventory"

    nav_entries = [
        {
            "slot": "nav_main",
            "order": 5,
            "label": _("Inventorize"),
            "icon": "fa-solid fa-glasses",
            "url": "inventory:inventorize-room-list",
            "required_permission": "core.can_inventorize",
            "show_condition": "active_inventory_exists",
        },
        {
            "slot": "nav_processes",
            "order": 40,
            "label": _("Inventorize"),
            "icon": "fa-solid fa-glasses",
            "url": "inventory:inventorize-room-list",
            "required_permission": "core.can_inventorize",
            "show_condition": "active_inventory_exists",
        },
        {
            "slot": "nav_processes",
            "order": 50,
            "label": _("SAP comparison"),
            "icon": "",
            "url": "admin:inventory_saplist_changelist",
            "required_permission": "core.change_inventory",
            "show_condition": "active_inventory_exists",
        },
    ]
