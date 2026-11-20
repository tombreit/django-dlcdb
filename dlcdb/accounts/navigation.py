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
        "description": _("Create users, set their passwords, see their groups and what they may do, deactivate them"),
        "search_terms": _("accounts, login, LDAP, superuser, password"),
        "icon": "bi bi-person-gear",
        "url": "accounts:users",
        # The accounts namespace has two entries: each lights up on its own pages.
        "active_url_names": ["users", "user_add", "user_detail", "user_set_password"],
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
        "url": "accounts:groups",
        "active_url_names": ["groups", "group_add", "group_detail", "group_delete"],
        "required_permission": "accounts.view_group",
    },
]
