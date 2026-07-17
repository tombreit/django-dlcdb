# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path
from .views import (
    relocate_views,
    procure_views,
)


app_name = "core"

urlpatterns = [
    path("devices/relocate/", relocate_views.DevicesRelocateView.as_view(), name="core_devices_relocate"),
    path("orderedrecord/procure/", procure_views.ProcureDeviceView.as_view(), name="core_procure_device"),
]
