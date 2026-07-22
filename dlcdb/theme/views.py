# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Shared HTMX endpoint backing the centralized device picker.

A single ``device_search`` view serves every picker source (lending, relocate,
…). The POST ``source`` token selects a registered :class:`theme.pickers.PickerSource`,
which supplies the tenant-scoped ``Device`` queryset and the required permission;
the ranking and rendering are shared. Login/permission are enforced dynamically
(the permission varies per source) the same HTMX-friendly way as
``core.utils.htmx``.
"""

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRefresh

from dlcdb.core.utils.device_search import search_devices

from .lifecycle_display import active_record_color_case
from .pickers import get_picker_source


@require_POST
def device_search(request):
    """Live-search the devices of the requested picker source. Empty query -> none."""
    source = get_picker_source(request.POST.get("source"))
    if source is None:
        return HttpResponseBadRequest("Unknown device picker source.")

    # Dynamic login/permission guard (perm depends on the source), HTMX-aware:
    # an unauthenticated or unauthorized request triggers a full client refresh
    # instead of swapping a login/403 page into the results container.
    if not request.user.is_authenticated:
        if getattr(request, "htmx", False):
            return HttpResponseClientRefresh()
        return redirect_to_login(request.get_full_path())
    if not request.user.has_perm(source.permission):
        messages.error(request, _("Permission denied."))
        return HttpResponseClientRefresh()

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
