# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 10,
        "label": _("Organization"),
        "group": "organization",
        "description": _("Name, address, IT contact, logos, room plan and documentation link"),
        "search_terms": _("branding, abbreviation, website, street, city, phone, email, figurative mark, docs"),
        "icon": "bi bi-building",
        "url": "organization:branding",
        "required_permission": "organization.view_branding",
    },
    {
        "slot": "nav_settings",
        "order": 11,
        "label": _("Organizational units"),
        "group": "organization",
        "description": _("The units persons belong to"),
        "search_terms": _("departments, institutes"),
        "icon": "bi bi-diagram-3",
        "url": "organization:unit:index",
        "required_permission": "core.view_organizationalunit",
    },
    {
        "slot": "nav_settings",
        "order": 12,
        "label": _("Positions"),
        "group": "organization",
        "description": _("The positions persons hold"),
        "search_terms": _("job titles, functions"),
        "icon": "bi bi-person-badge",
        "url": "organization:position:index",
        "required_permission": "core.view_organizationalposition",
    },
]
