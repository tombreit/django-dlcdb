# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.assets"
    verbose_name = _("Assets")

    def ready(self):
        # Register the relocate device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()

    nav_entries = [
        {
            "slot": "nav_main",
            "order": 10,
            "label": _("Devices"),
            "icon": "bi bi-pc-display",
            "url": "assets:device_index",
            "required_permission": "core.view_device",
            "active_url_names": {"device_index", "device_add", "device_detail", "person_search"},
        },
        {
            "slot": "nav_main",
            "order": 11,
            "label": _("Move"),
            "icon": "bi bi-arrows-move",
            "url": "assets:relocate",
            "required_permission": "core.add_inroomrecord",
            "active_url_names": {"relocate", "room_search"},
        },
    ]
