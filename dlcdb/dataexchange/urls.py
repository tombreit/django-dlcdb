# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "dataexchange"

urlpatterns = [
    path("import/", views.device_import, name="device_import"),
    path("import/<int:pk>/confirm/", views.device_import_confirm, name="device_import_confirm"),
    path("import/template/", views.device_import_template, name="device_import_template"),
]
