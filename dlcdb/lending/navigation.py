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
            "label": "Backend",
            "url": reverse("admin:core_lentrecord_changelist"),
            "icon_class": "bi bi-gear",
        },
        {
            "label": "Docs",
            "url": "/docs/guides/ausleihe.html",
            "icon_class": "bi bi-life-preserver",
        },
    ],
}
