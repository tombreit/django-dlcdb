# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import reverse


navigation = {
    "home_url": reverse("licenses:index"),
    "app_icon_class": "bi bi-c-circle",
    "navbar": [],
    "navbar_secondary": [
        {
            "label": "Backend",
            "url": reverse("admin:index"),
            "icon_class": "bi bi-gear",
        },
        {
            "label": "Docs",
            "url": "/docs/guides/lizenzen.html",
            "icon_class": "bi bi-life-preserver",
        },
    ],
}
