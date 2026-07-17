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
]
