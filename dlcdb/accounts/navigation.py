# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 10,
        "label": _("Users"),
        "group": "access",
        "description": _("Create users, set their groups and the Staff flag, deactivate them"),
        "search_terms": _("accounts, login, LDAP, superuser, password"),
        "icon": "bi bi-person-gear",
        "url": "admin:accounts_customuser_changelist",
        "required_permission": "accounts.view_customuser",
    },
    {
        "slot": "nav_settings",
        "order": 20,
        "label": _("Groups and permissions"),
        "group": "access",
        "description": _("What the members of a group may do"),
        "search_terms": _("roles, rights, LDAP groups"),
        "icon": "bi bi-shield-lock",
        "url": "admin:accounts_group_changelist",
        "required_permission": "accounts.view_group",
    },
]
