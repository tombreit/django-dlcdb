# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.urls import path

from . import views

app_name = "lending"

urlpatterns = [
    path("", views.index, name="index"),
    path("lend/", views.lend, name="lend"),
    path("person-search/", views.person_search, name="person_search"),
    path("<int:pk>/", views.lend, name="detail"),
    path("<int:pk>/print/", views.print_sheet, name="print_sheet"),
    path("record/<int:pk>/print/", views.print_lent_sheet, name="print_lent_sheet"),
]
