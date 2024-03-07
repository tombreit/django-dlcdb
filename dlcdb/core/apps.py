# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "dlcdb.core"
    verbose_name = "DLCDB Core"

    nav_entries = [
        {
            "slot": "nav_main",
            "order": 10,
            "label": "Verleih",
            "icon": "fa-solid fa-arrow-right-arrow-left",
            "url": "admin:core_lentrecord_changelist",
            "required_permission": "view_lentrecord",
        },
        {
            "slot": "nav_main",
            "order": 20,
            "label": "Devices",
            "icon": "fa-solid fa-barcode",
            "url": "admin:core_device_changelist",
            "required_permission": "view_device",
        },
        {
            "slot": "nav_main",
            "order": 40,
            "label": "Lizenzen",
            "icon": "fa-solid fa-scale-balanced",
            "url": "admin:core_licencerecord_changelist",
            "required_permission": "view_licencerecord",
        },
        {
            "slot": "nav_processes",
            "order": 10,
            "label": "Beschaffen",
            "icon": "",
            "url": "admin:core_orderedrecord_changelist",
            "required_permission": "view_orderedrecord",
        },
        {
            "slot": "nav_processes",
            "order": 20,
            "label": "Bulk-Import",
            "icon": "",
            "url": "admin:core_importerlist_changelist",
            "required_permission": "view_importerlist",
        },
        {
            "slot": "nav_processes",
            "order": 30,
            "label": "Bulk-Ausmustern",
            "icon": "",
            "url": "admin:core_removerlist_changelist",
            "required_permission": "view_removerlist",
        },
        {
            "slot": "nav_masterdata",
            "order": 10,
            "label": _("Rooms"),
            "icon": "fa-solid fa-door-open",
            "url": "admin:core_room_changelist",
            "required_permission": "view_room",
        },
        {
            "slot": "nav_masterdata",
            "order": 20,
            "label": _("Manufacturer"),
            "icon": "fa-solid fa-industry",
            "url": "admin:core_manufacturer_changelist",
            "required_permission": "view_manufacturer",
        },
        {
            "slot": "nav_masterdata",
            "order": 30,
            "label": _("Distributor"),
            "icon": "fa-solid fa-truck",
            "url": "admin:core_supplier_changelist",
            "required_permission": "view_supplier",
        },
        {
            "slot": "nav_masterdata",
            "order": 40,
            "label": _("Device types"),
            "icon": "fa-solid fa-palette",
            "url": "admin:core_devicetype_changelist",
            "required_permission": "view_devicetype",
        },
        {
            "slot": "nav_masterdata",
            "order": 50,
            "label": _("People"),
            "icon": "fa-solid fa-users",
            "url": "admin:core_person_changelist",
            "required_permission": "view_person",
        },
        {
            "slot": "nav_masterdata",
            "order": 60,
            "label": _("Records"),
            "icon": "fa-solid fa-layer-group",
            "url": "admin:core_record_changelist",
            "required_permission": "view_record",
        },
        {
            "slot": "nav_masterdata",
            "order": 70,
            "label": _("Removed records"),
            "icon": "fa-solid fa-layer-group",
            "url": "admin:core_removedrecord_changelist",
            "required_permission": "view_record",
        },
        {
            "slot": "nav_masterdata",
            "order": 80,
            "label": _("Inventories"),
            "icon": "fa-solid fa-glasses",
            "url": "admin:core_inventory_changelist",
            "required_permission": "change_inventory",
        },
        {
            "slot": "nav_masterdata",
            "order": 90,
            "label": _("Notes"),
            "icon": "fa-solid fa-comment",
            "url": "admin:core_note_changelist",
            "required_permission": "view_note",
        },
    ]
