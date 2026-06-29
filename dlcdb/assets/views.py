# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core.models import Record, Room
from dlcdb.core.utils.htmx import htmx_login_required, htmx_permission_required

from . import move
from .forms import RelocateForm
from .pickers import move_queryset

# Permission required to create the InRoomRecord that a relocation produces.
RELOCATE_PERM = "core.add_inroomrecord"

# Distinct search-input name so the room picker can share the relocate <form>
# with the device picker without HTMX mixing their query terms.
ROOM_SEARCH_PARAM = "q_room"

# Cap the room picker's "*" / live-search result list so the dropdown stays
# usable. (The device picker is intentionally uncapped: it relevance-ranks; see
# dlcdb.core.utils.device_search.)
SEARCH_RESULT_LIMIT = 25


@require_POST
@htmx_login_required
@htmx_permission_required(RELOCATE_PERM)
def room_search(request):
    """HTMX live-search backing the room picker. Empty query yields nothing."""
    value = (request.POST.get(ROOM_SEARCH_PARAM) or "").strip()
    rooms = Room.objects.filter(deleted_at__isnull=True)

    if not value:
        rooms = rooms.none()
    elif value != "*":
        rooms = rooms.filter(Q(number__icontains=value) | Q(nickname__icontains=value))

    rooms = rooms.order_by("number")[:SEARCH_RESULT_LIMIT]
    return TemplateResponse(
        request,
        "assets/includes/_room_search_results.html",
        {"rooms": rooms, "query": value},
    )


@login_required
def relocate(request):
    """
    Move one or more devices to a new room: pick the devices, pick a single
    target room, press "Move". Each device is relocated via the shared
    ``relocate_device`` state machine (mirroring the admin bulk action), which
    emits a per-device result message. Frontend replacement for the admin
    ``relocate`` action.
    """
    selected_devices = []
    selected_room = None

    # Scope the device field to the moveable, tenant-visible set so a user cannot
    # relocate another tenant's device — or an ORDERED/REMOVED one — by POSTing
    # its pk. Built once and reused for both the form and the re-render lookup.
    moveable_devices = move_queryset(request)

    if request.method == "POST":
        if not request.user.has_perm(RELOCATE_PERM):
            messages.error(request, _("You do not have permission to move devices."))
            return redirect("assets:relocate")

        form = RelocateForm(request.POST, device_queryset=moveable_devices, request=request)
        if form.is_valid():
            new_room = form.cleaned_data["new_room"]
            for device in form.cleaned_data["devices"]:
                result = move.relocate_device(device=device, new_room=new_room, user=request.user)
                messages.add_message(request, result.level, result.message)
            return redirect("assets:relocate")

        # Validation failed: keep the picked cards visible (they otherwise live
        # only in the submitted hidden fields). Resolve only well-formed ids so a
        # blank/garbage hidden field does not raise.
        device_ids = [pk for pk in request.POST.getlist("devices") if pk.isdigit()]
        room_id = request.POST.get("new_room") or ""
        if device_ids:
            selected_devices = list(moveable_devices.filter(pk__in=device_ids))
        if room_id.isdigit():
            selected_room = Room.objects.filter(pk=room_id).first()
    else:
        form = RelocateForm(device_queryset=moveable_devices, request=request)

    context = {
        "title": _("Move devices"),
        "form": form,
        "selected_devices": selected_devices,
        "selected_room": selected_room,
        "selected_any_lent": any(
            getattr(d.active_record, "record_type", None) == Record.LENT for d in selected_devices
        ),
    }
    return TemplateResponse(request, "assets/relocate.html", context)
