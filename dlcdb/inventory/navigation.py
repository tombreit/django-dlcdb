# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import reverse


navigation = {
    "home_url": reverse("inventory:inventorize-room-list"),
    "app_icon_class": "bi bi-eyeglasses",
    "navbar": [],
    "navbar_secondary": [
        {
            "label": "Devices",
            "url": reverse("inventory:search-devices"),
            "icon_class": "",
        },
        {
            "label": "VG bei MAs",
            "url": reverse("inventory:inventory-lending-report"),
            "icon_class": "",
        },
        {
            "label": "Docs",
            "url": "/docs/guides/inventur.html",
            "icon_class": "bi bi-book",
        },
    ],
    "navbar_status_template": "inventory/includes/navbar_status.html",
    "userdropdown_template": "inventory/includes/qr_toggle.html",
}
