# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import tomllib

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
