# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views_groups, views_users

app_name = "accounts"

urlpatterns = [
    path("groups/", views_groups.index, name="groups"),
    path("groups/add/", views_groups.add, name="group_add"),
    path("groups/<int:pk>/", views_groups.detail, name="group_detail"),
    path("groups/<int:pk>/delete/", views_groups.delete, name="group_delete"),
    path("users/", views_users.index, name="users"),
    path("users/<int:pk>/", views_users.detail, name="user_detail"),
    path("users/<int:pk>/active/", views_users.set_active, name="user_set_active"),
]
