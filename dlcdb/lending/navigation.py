# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import reverse


navigation = {
    "home_url": reverse("lending:index"),
    "app_icon_class": "bi bi-arrow-left-right",
    "navbar": [],
    "navbar_secondary": [
        {
            "label": "Docs",
            "url": "/docs/guides/ausleihe.html",
            "icon_class": "bi bi-life-preserver",
        },
    ],
}
