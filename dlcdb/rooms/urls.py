# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "rooms"

urlpatterns = [
    path("", views.room_index, name="index"),
    path("add/", views.room_add, name="add"),
    path("<int:pk>/", views.room_detail, name="detail"),
    path("reconcile/<int:reconcile_id>/", views.ReconcileRoomsView.as_view(), name="reconcile"),
]
