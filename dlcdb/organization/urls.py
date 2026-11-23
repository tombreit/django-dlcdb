# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import include, path

from . import views

app_name = "organization"

urlpatterns = [
    path("branding/", views.branding, name="branding"),
    path("units/", include(views.UnitViewSet().urls)),
    path("positions/", include(views.PositionViewSet().urls)),
]
