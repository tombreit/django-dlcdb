# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import apps


def navigation(request):
    navigation_dict = {}

    app_name = request.resolver_match.app_name

    try:
        app_config = apps.get_app_config(app_name)
        app_label = app_config.verbose_name
    except LookupError:
        pass

    try:
        module = __import__(f"dlcdb.{app_name}.navigation", fromlist=["navigation"])
        navigation_dict = getattr(module, "navigation", {})
    except ImportError as _import_error:
        # print(f"{_import_error=}. Ignoring navigation for {app_name=}")
        pass

    navigation_dict["app_label"] = app_label

    return {
        "navigation": navigation_dict,
    }
