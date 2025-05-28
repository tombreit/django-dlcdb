# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path
from . import views, views_calendar

app_name = "licenses"

urlpatterns = [
    # Calendar URLs
    path("<uuid:license_uuid>/calendar.ics", views_calendar.license_calendar, name="license_calendar"),
    # License management URLs
    path("<int:license_id>/history/", views.history, name="history"),
    path("<int:license_id>/edit/", views.edit, name="edit"),
    path("new/", views.new, name="new"),
    path("playground/", views._playground, name="playground"),
    path("", views.index, name="index"),
]
