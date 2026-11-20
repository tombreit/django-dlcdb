# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 5,
        "label": _("Tenants"),
        "group": "access",
        "description": _("Which groups see the devices of which tenant"),
        "search_terms": _("visibility, permissions, users, members, contact email"),
        "icon": "bi bi-diagram-3",
        "url": "tenants:index",
        "required_permission": "tenants.view_tenant",
    },
]
