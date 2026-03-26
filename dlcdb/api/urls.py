# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import include, path
from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views


router = routers.DefaultRouter()
router.register(r"devices", views.DeviceViewSet)
router.register(r"lent-records", views.LentRecordViewSet)
router.register(r"persons", views.PersonViewSet)
router.register(r"rooms", views.RoomViewSet)

urlpatterns = [
    path("", views.api_root, name="api-v2-root"),
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
