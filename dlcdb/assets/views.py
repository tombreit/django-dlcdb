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

from dlcdb.core.models import Device, Record, Room
from dlcdb.core.utils.htmx import htmx_login_required, htmx_permission_required
from dlcdb.core.utils.tenants import tenant_scoped_queryset

from . import move
from .forms import RelocateForm

# Permission required to create the InRoomRecord that a relocation produces.
RELOCATE_PERM = "core.add_inroomrecord"

# Distinct search-input names so the two pickers can share one <form> without
# HTMX mixing their query terms (see theme/includes/_picker.html).
DEVICE_SEARCH_PARAM = "q_device"
ROOM_SEARCH_PARAM = "q_room"

# Cap "*" / live-search result lists so the dropdown stays usable.
SEARCH_RESULT_LIMIT = 25

# Active record types that may be relocated. ORDERED (not yet arrived) and
# REMOVED (decommissioned) devices are not physically here to move; LOST stays
# moveable because a device that turns up is usually relocated when found.
MOVEABLE_RECORD_TYPES = (Record.INROOM, Record.LENT, Record.LOST)


def _moveable_devices(request):
    """
    Tenant-scoped queryset of relocatable devices, shared by the picker search
    and the relocate form. Only devices whose active record is one of
    ``MOVEABLE_RECORD_TYPES`` are exposed (ORDERED/REMOVED and record-less
    devices are excluded). Devices carry a ``tenant`` field directly; the shared
    scoping policy lives in ``dlcdb.core.utils.tenants``. ``active_record__person``
    is selected because the result card renders the borrower for LENT devices.
    """
    qs = Device.objects.select_related(
        "active_record__room", "active_record__person", "manufacturer", "device_type"
    ).filter(active_record__record_type__in=MOVEABLE_RECORD_TYPES)
    return tenant_scoped_queryset(qs, request, tenant_field="tenant")


@require_POST
@htmx_login_required
@htmx_permission_required(RELOCATE_PERM)
def device_search(request):
    """HTMX live-search backing the device picker. Empty query yields nothing."""
    value = (request.POST.get(DEVICE_SEARCH_PARAM) or "").strip()
    devices = _moveable_devices(request)

    if not value:
        devices = devices.none()
    elif value != "*":
        devices = devices.filter(
            Q(edv_id__icontains=value)
            | Q(sap_id__icontains=value)
            | Q(manufacturer__name__icontains=value)
            | Q(series__icontains=value)
            | Q(serial_number__icontains=value)
        )

    devices = devices.order_by("edv_id")[:SEARCH_RESULT_LIMIT]
    return TemplateResponse(
        request,
        "assets/includes/_device_search_results.html",
        {"devices": devices, "query": value},
    )


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
    Move a single device to a new room: pick a device, pick a target room,
    press "Move". Frontend replacement for the admin ``relocate`` action.
    """
    selected_device = None
    selected_room = None

    # Scope the device field to the moveable, tenant-visible set so a user cannot
    # relocate another tenant's device — or an ORDERED/REMOVED one — by POSTing
    # its pk. Built once and reused for both the form and the re-render lookup.
    moveable_devices = _moveable_devices(request)

    if request.method == "POST":
        if not request.user.has_perm(RELOCATE_PERM):
            messages.error(request, _("You do not have permission to move devices."))
            return redirect("assets:relocate")

        form = RelocateForm(request.POST, device_queryset=moveable_devices)
        if form.is_valid():
            result = move.relocate_device(
                device=form.cleaned_data["device"],
                new_room=form.cleaned_data["new_room"],
                user=request.user,
            )
            messages.add_message(request, result.level, result.message)
            return redirect("assets:relocate")

        # Validation failed: keep the picked cards visible (they otherwise live
        # only in the submitted hidden fields). Resolve only well-formed ids so a
        # blank/garbage hidden field does not raise.
        device_id = request.POST.get("device") or ""
        room_id = request.POST.get("new_room") or ""
        if device_id.isdigit():
            selected_device = moveable_devices.filter(pk=device_id).first()
        if room_id.isdigit():
            selected_room = Room.objects.filter(pk=room_id).first()
    else:
        form = RelocateForm(device_queryset=moveable_devices)

    context = {
        "title": _("Move device"),
        "form": form,
        "selected_device": selected_device,
        "selected_room": selected_room,
        "selected_device_is_lent": bool(
            selected_device and getattr(selected_device.active_record, "record_type", None) == Record.LENT
        ),
    }
    return TemplateResponse(request, "assets/relocate.html", context)
