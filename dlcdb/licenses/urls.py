# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path
from . import views

app_name = "licenses"

urlpatterns = [
    path("<int:license_id>/history/", views.history, name="history"),
    path("<int:license_id>/edit/", views.edit, name="edit"),
    path("new/", views.new, name="new"),
    path("", views.index, name="index"),
]
