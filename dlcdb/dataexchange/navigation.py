# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 10,
        "label": _("Bulk import"),
        "group": "data",
        "description": _("Import devices from a CSV file, with a preview before anything is saved"),
        "search_terms": _("upload, template, devices, SAP"),
        "icon": "bi bi-file-earmark-arrow-down",
        # The import itself; its page links the import history.
        "url": "dataexchange:device_import",
        "required_permission": "core.add_device",
        "active_url_names": {
            "importer_index",
            "importer_detail",
            "device_import",
            "device_import_confirm",
            "device_import_template",
        },
    },
    {
        "slot": "nav_settings",
        "order": 20,
        "label": _("Bulk decommissioning"),
        "group": "data",
        "description": _("Remove many devices at once, listed in a CSV file"),
        "search_terms": _("decommission, retire, dispose, upload, removed"),
        "icon": "bi bi-trash3",
        "url": "admin:dataexchange_removerlist_changelist",
        "required_permission": "dataexchange.view_removerlist",
    },
    {
        "slot": "nav_settings",
        "order": 40,
        "label": _("HR API sync configuration"),
        "group": "integrations",
        "description": _("Connection to the HR system, the room name rule and the latest runs"),
        "search_terms": _("UDB, token, URL, persons, people, regular expression, sync now"),
        "icon": "bi bi-arrow-clockwise",
        "url": "dataexchange:hr_sync",
        "required_permission": "dataexchange.view_udbsyncconfiguration",
        "active_url_names": {"hr_sync"},
    },
    {
        "slot": "nav_settings",
        "order": 45,
        "label": _("HR sync runs"),
        "group": "integrations",
        "description": _("Every run of the HR sync with its notes; the HR sync page shows the latest five"),
        "search_terms": _("UDB, log, errors, missing rooms"),
        "icon": "bi bi-clock-history",
        "url": "admin:dataexchange_udbsyncrun_changelist",
        "required_permission": "dataexchange.view_udbsyncrun",
    },
]
