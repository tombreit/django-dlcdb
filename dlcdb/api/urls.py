# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import include, path
from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register(r"devices", views.DeviceViewSet)
router.register(r"lent-records", views.LentRecordViewSet)
router.register(r"persons", views.PersonViewSet)
router.register(r"rooms", views.RoomViewSet)

urlpatterns = [
    path("", views.api_root, name="api-v2-root"),
    path("", include(router.urls)),
]
