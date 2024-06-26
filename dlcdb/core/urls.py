# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path
from django.views.decorators.cache import cache_page
from .views import (
    room_views,
    relocate_views,
    procure_views,
    lent_management_views,
    dashboard_views,
)


app_name = "core"


stats_cache_timeout = 60 * 60 * 12

urlpatterns = [
    path("dashboard/", dashboard_views.DashboardView.as_view(), name="core_dashboard"),
    path(
        "stats/<str:record_type_name>/",
        cache_page(stats_cache_timeout)(dashboard_views.get_chartjs_data),
        name="get_chartjs_data",
    ),
    path("rooms/reconcile/<int:reconcile_id>", room_views.ReconcileRoomsView.as_view(), name="reconcile-rooms"),
    path("devices/relocate/", relocate_views.DevicesRelocateView.as_view(), name="core_devices_relocate"),
    path("orderedrecord/procure/", procure_views.ProcureDeviceView.as_view(), name="core_procure_device"),
    path("lentrecord/print/<int:pk>/", lent_management_views.print_lent_sheet, name="print_lent_sheet"),
]
