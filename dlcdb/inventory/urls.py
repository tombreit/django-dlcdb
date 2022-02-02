from django.conf import settings
from django.urls import path, re_path
from .views import (
    InventorizeRoomListView,
    InventorizeRoomView,
    QrCodesForRoomDetailView,
    InventoryReportView,
    DevicesSearchView,
    SapCompareListView,
)


app_name = 'inventory'

urlpatterns = [
    path('', InventorizeRoomListView.as_view(), name='inventorize-room-list'),
    path('room/<int:pk>', InventorizeRoomView.as_view(), name='inventorize-room'),
    path('room/<uuid:uuid>', InventorizeRoomView.as_view(), name='inventorize-room'),
    path('room/<int:pk>/qrs/', QrCodesForRoomDetailView.as_view(), name='qr-room-printout'),
    path('room/<int:pk>', InventorizeRoomView.as_view(), name='inventorize-room'),
    path('misc/inventory_lending_report', InventoryReportView.as_view(), name="inventory-lending-report"),
    path('devices', DevicesSearchView.as_view(), name='search-devices'),
    path('saplist/compare_sap_list/<int:pk>/', SapCompareListView.as_view(), name='compare-sap-list'),
]