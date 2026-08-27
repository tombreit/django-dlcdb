# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Shared HTMX endpoint backing the centralized device picker.

A single ``device_search`` view serves every picker source (lending, relocate,
…). The POST ``source`` token selects a registered :class:`theme.pickers.PickerSource`,
which supplies the tenant-scoped ``Device`` queryset and the required permission;
the ranking and rendering are shared. The login guard is the shared
``htmx_login_required``; the permission check has to stay inline because which
permission applies is only known once the source is resolved, but it follows the
same contract as ``htmx_permission_required``.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRefresh

from dlcdb.core.utils.device_search import search_devices
from dlcdb.core.utils.htmx import htmx_login_required

from .lifecycle_display import active_record_color_case
from .pickers import get_picker_source


@require_POST
@htmx_login_required
def device_search(request):
    """Live-search the devices of the requested picker source. Empty query -> none."""
    source = get_picker_source(request.POST.get("source"))
    if source is None:
        return HttpResponseBadRequest("Unknown device picker source.")

    # The permission depends on the source, so it cannot be a static decorator.
    # Same contract as core.utils.htmx.htmx_permission_required: an HTMX request
    # gets a client refresh (never a 403 page swapped into the results
    # container), a plain navigation gets the ordinary 403.
    if not source.grants_access(request.user):
        message = _("Permission denied.")
        if getattr(request, "htmx", False):
            messages.error(request, message)
            return HttpResponseClientRefresh()
        raise PermissionDenied(message)

    value = (request.POST.get(source.search_param) or "").strip()
    devices = search_devices(source.get_queryset(request), value).annotate(state_color=active_record_color_case())

    # Multi-select: drop devices already chosen in the picker (their hidden inputs
    # ride along via hx-include) so the dropdown only offers fresh choices.
    if source.exclude_param:
        selected_ids = [pk for pk in request.POST.getlist(source.exclude_param) if pk.isdigit()]
        if selected_ids:
            devices = devices.exclude(pk__in=selected_ids)

    return TemplateResponse(
        request,
        "theme/widgets/device_picker/_results.html",
        {"devices": devices, "query": value},
    )
