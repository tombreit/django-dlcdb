from django.urls import path
from .views import (
    room_views,
    relocate_views,
)


app_name = 'core'

urlpatterns = [
    path('rooms/reconcile/<int:reconcile_id>', room_views.ReconcileRoomsView.as_view(), name='reconcile-rooms'),
    path('devices/relocate/', relocate_views.DevicesRelocateView.as_view(), name='core_devices_relocate'),
]