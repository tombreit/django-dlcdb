# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/toggle/", views.toggle, name="toggle"),
    path("<int:pk>/trigger/", views.trigger, name="trigger"),
    path("", views.index, name="index"),
]
