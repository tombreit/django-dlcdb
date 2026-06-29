# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "theme"

urlpatterns = [
    path("device-search/", views.device_search, name="device_search"),
]
