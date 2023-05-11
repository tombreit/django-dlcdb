from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.InventorizeRoomListView.as_view(), name='inventorize-room-list'),
    path('room/<int:pk>/', views.InventorizeRoomView.as_view(), name='inventorize-room'),
    path('room/<uuid:uuid>', views.InventorizeRoomView.as_view(), name='inventorize-room'),
    path('room/<int:pk>/qrs/', views.QrCodesForRoomDetailView.as_view(), name='qr-room-printout'),
    path('room/<int:pk>', views.InventorizeRoomView.as_view(), name='inventorize-room'),
    path('room/<int:room_pk>/note/', views.update_room_note, name='room-note-update'),
    path('misc/inventory_lending_report', views.InventoryReportView.as_view(), name="inventory-lending-report"),
    path('devices', views.DevicesSearchView.as_view(), name='search-devices'),
    path('saplist/compare_sap_list/<int:pk>/', views.SapCompareListView.as_view(), name='compare-sap-list'),
    path('update-qrtoggle', views.update_session_qrtoggle, name='update-qrtoggle')
]
