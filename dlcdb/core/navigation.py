# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_main",
        "order": 10,
        "label": _("Lending"),
        "icon": "bi bi-arrow-left-right",
        "url": "lending:index",
        "required_permission": "view_lentrecord",
    },
    # {
    #     "slot": "nav_main",
    #     "order": 20,
    #     "label": _("Devices"),
    #     "icon": "bi bi-upc",
    #     "url": "admin:core_device_changelist",
    #     "required_permission": "view_device",
    # },
    # This slot is set in the app licenses.navigation module
    # {
    #     "slot": "nav_main",
    #     "order": 40,
    #     "label": _("Licenses"),
    #     "icon": "bi bi-bank2",
    #     "url": "licenses:index",
    #     "required_permission": "view_licencerecord",
    # },
    {
        "slot": "nav_processes",
        "order": 10,
        "label": _("Procurement"),
        "icon": "",
        "url": "admin:core_orderedrecord_changelist",
        "required_permission": "view_orderedrecord",
    },
    {
        "slot": "nav_masterdata",
        "order": 10,
        "label": _("Rooms"),
        "icon": "bi bi-door-open",
        "url": "admin:core_room_changelist",
        "required_permission": "view_room",
    },
    {
        "slot": "nav_masterdata",
        "order": 20,
        "label": _("Manufacturer"),
        "icon": "bi bi-building",
        "url": "admin:core_manufacturer_changelist",
        "required_permission": "view_manufacturer",
    },
    {
        "slot": "nav_masterdata",
        "order": 30,
        "label": _("Distributor"),
        "icon": "bi bi-truck",
        "url": "admin:core_supplier_changelist",
        "required_permission": "view_supplier",
    },
    {
        "slot": "nav_masterdata",
        "order": 40,
        "label": _("Device types"),
        "icon": "bi bi-palette",
        "url": "admin:core_devicetype_changelist",
        "required_permission": "view_devicetype",
    },
    {
        "slot": "nav_masterdata",
        "order": 50,
        "label": _("People"),
        "icon": "bi bi-people",
        "url": "admin:core_person_changelist",
        "required_permission": "view_person",
    },
    {
        "slot": "nav_masterdata",
        "order": 60,
        "label": _("Records"),
        "icon": "bi bi-stack",
        "url": "admin:core_record_changelist",
        "required_permission": "view_record",
    },
    {
        "slot": "nav_masterdata",
        "order": 70,
        "label": _("Removed records"),
        "icon": "bi bi-stack",
        "url": "admin:core_removedrecord_changelist",
        "required_permission": "view_record",
    },
    {
        "slot": "nav_masterdata",
        "order": 80,
        "label": _("Inventories"),
        "icon": "bi bi-eyeglasses",
        "url": "admin:core_inventory_changelist",
        "required_permission": "change_inventory",
    },
    {
        "slot": "nav_masterdata",
        "order": 90,
        "label": _("Notes"),
        "icon": "bi bi-chat",
        "url": "admin:core_note_changelist",
        "required_permission": "view_note",
    },
]
