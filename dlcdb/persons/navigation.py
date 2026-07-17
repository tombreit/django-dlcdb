# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_masterdata",
        "order": 50,
        "label": _("People"),
        "icon": "bi bi-people",
        "url": "persons:index",
        "required_permission": "core.view_person",
    },
]
