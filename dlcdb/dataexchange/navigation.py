# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _


nav_entries = [
    {
        "slot": "nav_processes",
        "order": 20,
        "label": _("Bulk import"),
        "icon": "",
        "url": "admin:dataexchange_importerlist_changelist",
        "required_permission": "dataexchange.view_importerlist",
    },
    {
        "slot": "nav_processes",
        "order": 30,
        "label": _("Bulk decommissioning"),
        "icon": "",
        "url": "admin:dataexchange_removerlist_changelist",
        "required_permission": "dataexchange.view_removerlist",
    },
    {
        "slot": "nav_settings",
        "order": 40,
        "label": _("UDB sync configuration"),
        "icon": "bi bi-arrow-clockwise",
        "url": "admin:dataexchange_udbsyncconfiguration_changelist",
        "required_permission": "dataexchange.view_udbsyncconfiguration",
    },
]
