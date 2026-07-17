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
    path("device-types/", views.device_type_index, name="device_type_index"),
    path("device-types/add/", views.device_type_add, name="device_type_add"),
    path("device-types/<int:pk>/", views.device_type_detail, name="device_type_detail"),
    path("manufacturers/", views.manufacturer_index, name="manufacturer_index"),
    path("manufacturers/add/", views.manufacturer_add, name="manufacturer_add"),
    path("manufacturers/<int:pk>/", views.manufacturer_detail, name="manufacturer_detail"),
    path("suppliers/", views.supplier_index, name="supplier_index"),
    path("suppliers/add/", views.supplier_add, name="supplier_add"),
    path("suppliers/<int:pk>/", views.supplier_detail, name="supplier_detail"),
    path("person-search/", views.person_search, name="person_search"),
    path("relocate/", views.relocate, name="relocate"),
    path("room-search/", views.room_search, name="room_search"),
]
