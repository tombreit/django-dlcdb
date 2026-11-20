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
        "description": _("Name, address, IT contact, logos, room plan and documentation link; units and positions"),
        "search_terms": _(
            "branding, abbreviation, website, street, city, phone, email, figurative mark, docs, departments, job titles"
        ),
        "icon": "bi bi-building",
        "url": "organization:branding",
        "required_permission": "organization.view_branding",
    },
]
