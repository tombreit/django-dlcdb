from django.urls import path
from .views import (
    room_views,
    relocate_views,
    procure_views,
    lent_management_views,
    dashboard_views,
)


app_name = 'core'

urlpatterns = [
    path('dashboard/', dashboard_views.DashboardView.as_view(), name='core_dashboard'),
    path('rooms/reconcile/<int:reconcile_id>', room_views.ReconcileRoomsView.as_view(), name='reconcile-rooms'),
    path('devices/relocate/', relocate_views.DevicesRelocateView.as_view(), name='core_devices_relocate'),
    path('orderedrecord/procure/', procure_views.ProcureDeviceView.as_view(), name='core_procure_device'),
    path('lentrecord/print/<int:pk>/', lent_management_views.PrintLentSheetView.as_view(), name='print_lent_sheet'),
]
