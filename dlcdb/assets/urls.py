# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "assets"

urlpatterns = [
    path("devices/", views.device_index, name="device_index"),
    path("devices/add/", views.device_add, name="device_add"),
    path("devices/<int:pk>/", views.device_detail, name="device_detail"),
    path("relocate/", views.relocate, name="relocate"),
    path("room-search/", views.room_search, name="room_search"),
]
