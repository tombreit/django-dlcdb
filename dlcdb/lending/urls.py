# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views, views_profiles

app_name = "lending"

urlpatterns = [
    path("", views.index, name="index"),
    path("export.csv", views.lending_export_csv, name="export_csv"),
    path("lend/", views.lend, name="lend"),
    path("person-search/", views.person_search, name="person_search"),
    path("configuration/", views.configuration, name="configuration"),
    path("profiles/add/", views_profiles.profile_add, name="profile_add"),
    path("profiles/<int:pk>/", views_profiles.profile_detail, name="profile_detail"),
    path("<int:pk>/", views.lend, name="detail"),
    path("<int:pk>/print/", views.print_sheet, name="print_sheet"),
]
