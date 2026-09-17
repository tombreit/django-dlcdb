# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "dataexchange"

urlpatterns = [
    path("import/", views.device_import, name="device_import"),
    path("import/<int:pk>/confirm/", views.device_import_confirm, name="device_import_confirm"),
    path("imports/", views.importer_index, name="importer_index"),
    path("imports/<int:pk>/", views.importer_detail, name="importer_detail"),
    path("import/template/", views.device_import_template, name="device_import_template"),
]
