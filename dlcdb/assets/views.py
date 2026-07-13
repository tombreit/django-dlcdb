# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core.models import Device, Record, Room
from dlcdb.core.utils.htmx import htmx_login_required, htmx_permission_required
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.filterbar import build_filterbar

from . import move
from .filters import DeviceFilter
from .forms import DeviceForm, RelocateForm
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


def _device_queryset(request):
    """Devices visible in the frontend, with every relation used by its rows."""
    queryset = Device.objects.select_related(
        "active_record__room",
        "active_record__person",
        "active_record__inventory",
        "device_type",
        "manufacturer",
        "supplier",
        "contact_person_internal",
        "tenant",
    )
    return tenant_scoped_queryset(queryset, request, tenant_field="tenant")


@permission_required("core.view_device", raise_exception=True)
def device_index(request):
    """Tenant-scoped Device overview, with progressive HTMX filtering."""
    template = "assets/devices/index.html#device-list" if request.htmx else "assets/devices/index.html"
    base_queryset = _device_queryset(request)

    # The filter always receives an ordering. This makes a direct page visit
    # predictable while preserving explicit links and column-header choices.
    data = request.GET.copy()
    data.setdefault("ordering", "-modified")
    device_filter = DeviceFilter(data, queryset=base_queryset, request=request)

    context = {
        "filter": device_filter,
        "filterbar": build_filterbar(
            device_filter,
            request,
            target="#device-list",
            search_placeholder=_("Search IT ID, serial number, model..."),
        ),
        "current_ordering": data["ordering"],
        "device_filtered_count": device_filter.qs.count(),
        "device_total_count": base_queryset.count(),
    }
    return TemplateResponse(request, template, context)


def _get_device(request, pk):
    """Fetch a visible device, returning 404 for a device outside its tenant."""
    return get_object_or_404(_device_queryset(request), pk=pk)


@permission_required("core.add_device", raise_exception=True)
def device_add(request):
    """Create a device and attach its audit information to the current user."""
    form = DeviceForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        device = form.save(commit=False)
        if not request.user.is_superuser:
            device.tenant = getattr(request, "tenant", None)
        device.user, device.username = get_denormalized_user(request.user)
        device.save()
        messages.success(request, _("Device “%(device)s” was created.") % {"device": device})
        return redirect("assets:device_detail", pk=device.pk)

    return TemplateResponse(
        request,
        "assets/devices/form.html",
        {"form": form, "title": _("Add device"), "submit_label": _("Create device")},
    )


@permission_required("core.view_device", raise_exception=True)
def device_detail(request, pk):
    """Read and edit one device in the same straightforward page."""
    device = _get_device(request, pk)
    can_change = request.user.has_perm("core.change_device")

    if request.method == "POST":
        if not can_change:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        form = DeviceForm(request.POST, instance=device, request=request)
        if form.is_valid():
            saved_device = form.save(commit=False)
            if not request.user.is_superuser:
                saved_device.tenant = getattr(request, "tenant", None)
            saved_device.user, saved_device.username = get_denormalized_user(request.user)
            saved_device.save()
            messages.success(request, _("Device “%(device)s” was updated.") % {"device": saved_device})
            return redirect("assets:device_detail", pk=saved_device.pk)
    else:
        form = DeviceForm(instance=device, request=request)

    return TemplateResponse(
        request,
        "assets/devices/detail.html",
        {"device": device, "form": form, "can_change": can_change},
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
