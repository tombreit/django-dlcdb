# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "persons"

urlpatterns = [
    path("", views.person_index, name="index"),
    path("add/", views.person_add, name="add"),
    path("<int:pk>/", views.person_detail, name="detail"),
]
