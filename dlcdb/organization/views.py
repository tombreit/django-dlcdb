# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import FileResponse, HttpRequest
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from dlcdb.core.utils.htmx import htmx_permission_required
from dlcdb.theme.settings_page import settings_page

from .forms import BrandingForm


@login_not_required  # the login page shows it too
@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> FileResponse:
    file = settings.BASE_DIR / "dlcdb" / "theme" / "static" / "theme" / "branding" / "favicon.ico"

    return FileResponse(file.open("rb"))


@htmx_permission_required("organization.view_branding")
def branding(request):
    """Settings › Organization: the organisation's names, address, IT contact, logos and room plan."""
    return settings_page(request, BrandingForm, icon="bi-building", template="organization/branding.html")
