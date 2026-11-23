# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import include, path

from . import views

app_name = "assets"

urlpatterns = [
    path("devices/", views.device_index, name="device_index"),
    path("devices/export.csv", views.device_export_csv, name="device_export_csv"),
    path("devices/add/", views.device_add, name="device_add"),
    path("devices/<int:pk>/", views.device_detail, name="device_detail"),
    path("devices/<int:pk>/history/", views.device_history, name="device_history"),
    path("devices/<int:pk>/order/", views.device_order, name="device_order"),
    path("devices/<int:pk>/state/<slug:name>/", views.device_transition, name="device_transition"),
    path("device-types/", include(views.DeviceTypeViewSet().urls)),
    path("manufacturers/", include(views.ManufacturerViewSet().urls)),
    path("suppliers/", include(views.SupplierViewSet().urls)),
    path("records/", views.record_index, name="record_index"),
    path("records/<int:pk>/", views.record_detail, name="record_detail"),
    path("records/<int:pk>/attachments/", views.record_attachments, name="record_attachments"),
    path("person-search/", views.person_search, name="person_search"),
    path("relocate/", views.relocate, name="relocate"),
    path("room-search/", views.room_search, name="room_search"),
]
