# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .models import Branding


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    branding = Branding.load()
    if branding.organization_favicon:
        file = branding.organization_favicon.file
    else:
        file = settings.STATIC_ROOT / "branding" / "favicon.ico"

    return FileResponse(file.open("rb"))
