# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path("", views.journal_index, name="index"),
    path("<int:pk>/", views.journal_detail, name="detail"),
]
