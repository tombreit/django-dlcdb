# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import reverse


navigation = {
    "home_url": reverse("smallstuff:person_search"),
    "app_icon_class": "bi bi-handbag",
    "navbar": [],
    "userdropdown": [
        {
            "label": "Backend",
            "url": reverse("admin:smallstuff_thing_changelist"),
            "icon_class": "bi bi-gear",
        },
        {
            "label": "Docs",
            "url": "/docs/guides/kleinkram.html",
            "icon_class": "bi bi-life-preserver",
        },
    ],
}
