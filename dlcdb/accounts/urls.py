# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views_groups

app_name = "accounts"

urlpatterns = [
    path("groups/", views_groups.index, name="groups"),
    path("groups/<int:pk>/", views_groups.detail, name="group_detail"),
]
