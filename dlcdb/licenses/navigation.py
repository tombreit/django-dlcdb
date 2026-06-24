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
            "label": "Docs",
            "url": "/docs/guides/lizenzen.html",
            "icon_class": "bi bi-book",
        },
    ],
}
