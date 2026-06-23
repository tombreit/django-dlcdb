# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import tomllib

from django.apps import apps
from django.conf import settings


def _read_project_meta():
    """
    Read project identity (version + URLs) from pyproject.toml once at import.

    pyproject.toml ships with the source tree (the container image does a plain
    ``COPY . .``), so this is reliable in dev and in production, unlike
    importlib.metadata (the project is run from source, not pip-installed).
    Any failure degrades gracefully to empty strings so the footer just omits
    the affected item.
    """
    version = repository_url = issues_url = ""
    try:
        with open(settings.BASE_DIR / "pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        project = data.get("project", {})
        urls = project.get("urls", {})
        version = project.get("version", "")
        repository_url = urls.get("Repository", "") or urls.get("Homepage", "")
        issues_url = urls.get("Issues", "")
    except (OSError, tomllib.TOMLDecodeError):
        pass
    return version, repository_url, issues_url


_PROJECT_VERSION, _PROJECT_REPOSITORY_URL, _PROJECT_ISSUES_URL = _read_project_meta()


def project_meta(request):
    """Expose project version and source/issue URLs (used by the theme footer)."""
    return {
        "project_version": _PROJECT_VERSION,
        "project_repository_url": _PROJECT_REPOSITORY_URL,
        "project_issues_url": _PROJECT_ISSUES_URL,
    }


def navigation(request):
    navigation_dict = {}

    app_name = request.resolver_match.app_name
    app_label = None

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

    if app_label:
        navigation_dict["app_label"] = app_label

    return {
        "navigation": navigation_dict,
    }
