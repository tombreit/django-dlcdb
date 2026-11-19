# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views, views_masterdata

app_name = "organization"

urlpatterns = [
    path("branding/", views.branding, name="branding"),
    path("units/add/", views_masterdata.unit_add, name="unit_add"),
    path("units/<int:pk>/", views_masterdata.unit_detail, name="unit_detail"),
    path("units/<int:pk>/delete/", views_masterdata.unit_delete, name="unit_delete"),
    path("positions/add/", views_masterdata.position_add, name="position_add"),
    path("positions/<int:pk>/", views_masterdata.position_detail, name="position_detail"),
    path("positions/<int:pk>/delete/", views_masterdata.position_delete, name="position_delete"),
]
