# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_main",
        "order": 5,
        "label": _("Inventorize"),
        "icon": "bi bi-eyeglasses",
        "url": "inventory:inventorize-room-list",
        "required_permission": "core.can_inventorize",
        "show_condition": "active_inventory_exists",
    },
    {
        "slot": "nav_settings",
        "order": 30,
        "label": _("Inventories"),
        "group": "data",
        "description": _("Start and end an inventory"),
        "search_terms": _("stocktaking, inventorize, active inventory"),
        "icon": "bi bi-eyeglasses",
        "url": "admin:core_inventory_changelist",
        "required_permission": "core.change_inventory",
    },
    {
        "slot": "nav_settings",
        "order": 40,
        "label": _("SAP comparison"),
        "group": "data",
        "description": _("Compare the active inventory with an SAP export"),
        "search_terms": _("upload, CSV, assets, inventory"),
        "icon": "bi bi-file-earmark-diff",
        "url": "admin:inventory_saplist_changelist",
        "required_permission": "core.change_inventory",
        "show_condition": "active_inventory_exists",
    },
]

nav_focus = {
    "navbar": [
        {
            "label": _("Rooms"),
            "url": "inventory:inventorize-room-list",
            "icon": "bi bi-door-open",
        },
    ],
    "navbar_secondary": [
        {
            "label": _("Devices"),
            "url": "inventory:search-devices",
            "icon": "",
        },
        {
            "label": _("VG bei MAs"),
            "url": "inventory:inventory-lending-report",
            "icon": "",
        },
        {
            "label": _("Docs"),
            "href": "/docs/guides/inventur.html",
            "icon": "bi bi-book",
        },
    ],
    "navbar_status_template": "inventory/includes/navbar_status.html",
    "userdropdown_template": "inventory/includes/qr_toggle.html",
}
