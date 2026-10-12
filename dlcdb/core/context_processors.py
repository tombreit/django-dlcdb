# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings


def django_settings(request):
    """
    Expose some cherry picked Django settings to the templates.
    """
    return {
        "django_settings": {
            "DEFAULT_FROM_EMAIL": settings.DEFAULT_FROM_EMAIL,
        }
    }
