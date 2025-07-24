# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventorizeRoomListView.as_view(), name="inventorize-room-list"),
    path("room/<int:pk>/qrs/", views.QrCodesForRoomDetailView.as_view(), name="qr-room-printout"),
    path("room/<int:pk>/", views.InventorizeRoomView.as_view(), name="inventorize-room"),
    path("note-btn/<str:obj_type>/<uuid:obj_uuid>/", views.get_note_btn, name="get_note_btn"),
    path("note/<int:pk>/delete/", views.delete_note_view, name="note-delete"),
    path("note/<str:obj_type>/<uuid:obj_uuid>/", views.update_note_view, name="note-update"),
    path("misc/inventory_lending_report/", views.InventoryReportView.as_view(), name="inventory-lending-report"),
    path("devices/", views.search_devices, name="search-devices"),
    path("saplist/compare_sap_list/<int:pk>/", views.SapCompareListView.as_view(), name="compare-sap-list"),
    path("update-qrtoggle/", views.update_session_qrtoggle, name="update-qrtoggle"),
]
