# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 5,
        "label": _("Tenants"),
        "icon": "bi bi-diagram-3",
        "url": "tenants:index",
        "required_permission": "tenants.view_tenant",
    },
]
