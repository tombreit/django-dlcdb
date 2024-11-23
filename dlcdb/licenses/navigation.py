# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import reverse


navigation = {
    "home_url": reverse("licenses:index"),
    "app_icon_class": "bi bi-c-circle",
    "navbar": [],
    "userdropdown": [
        {
            "label": "Backend",
            "url": reverse("admin:index"),
            "icon_class": "bi bi-gear",
        },
        {
            "label": "Docs",
            "url": "/docs/guides/licenses.html",
            "icon_class": "bi bi-life-preserver",
        },
    ],
}
