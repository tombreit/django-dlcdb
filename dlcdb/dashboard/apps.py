# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
# from django.utils.translation import gettext_lazy as _


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.dashboard"

    # nav_entries = [
    #     {
    #         "slot": "nav_main",
    #         "order": 0,
    #         "label": _("Dashboard"),
    #         "icon": "bi bi-speedometer2",
    #         "url": "dashboard:index",
    #         # "true" disables permission checking, so the dashboard is visible
    #         # to any authenticated user (see core.context_processors.nav).
    #         "required_permission": "true",
    #     },
    # ]
