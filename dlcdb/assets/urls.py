# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "assets"

urlpatterns = [
    path("relocate/", views.relocate, name="relocate"),
    path("device-search/", views.device_search, name="device_search"),
    path("room-search/", views.room_search, name="room_search"),
]
