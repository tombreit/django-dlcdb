# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dlcdb import __version__

# Kept in step with [project.urls] in pyproject.toml.
REPOSITORY_URL = "https://gitlab.gwdg.de/t.breitner/django-dlcdb"
ISSUES_URL = f"{REPOSITORY_URL}/-/issues"


def project_meta(request):
    """Expose project version and source/issue URLs (used by the theme footer)."""
    return {
        "project_version": __version__,
        "project_repository_url": REPOSITORY_URL,
        "project_issues_url": ISSUES_URL,
    }
