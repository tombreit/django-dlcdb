# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_main",
        "order": 11,
        "label": _("Move"),
        "icon": "bi bi-arrows-move",
        "url": "assets:relocate",
        "required_permission": "core.add_inroomrecord",
        "active_url_names": {"relocate", "room_search"},
    },
    {
        "slot": "nav_main",
        "order": 12,
        "label": _("Devices"),
        "icon": "bi bi-pc-display",
        "url": "assets:device_index",
        "required_permission": "core.view_device",
        "active_url_names": {"device_index", "device_add", "device_detail", "person_search"},
    },
    {
        "slot": "nav_masterdata",
        "order": 20,
        "label": _("Manufacturer"),
        "icon": "bi bi-building",
        "url": "assets:manufacturer_index",
        "required_permission": "core.view_manufacturer",
        "active_url_names": {"manufacturer_index", "manufacturer_add", "manufacturer_detail"},
    },
    {
        "slot": "nav_masterdata",
        "order": 30,
        "label": _("Distributor"),
        "icon": "bi bi-truck",
        "url": "assets:supplier_index",
        "required_permission": "core.view_supplier",
        "active_url_names": {"supplier_index", "supplier_add", "supplier_detail"},
    },
    {
        "slot": "nav_masterdata",
        "order": 40,
        "label": _("Device types"),
        "icon": "bi bi-palette",
        "url": "assets:device_type_index",
        "required_permission": "core.view_devicetype",
        "active_url_names": {"device_type_index", "device_type_add", "device_type_detail"},
    },
]
