# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from dlcdb.core.models import Device, Person
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.core.utils.htmx import htmx_login_required, htmx_permission_required
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.pagination import paginate

from ..filters import DeviceFilter
from ..forms import DeviceForm

# Rows this many per page. The old changelist rendered up to 5000 rows at once;
# paging keeps the HTMX payload and template render small (the SQL was never the
# problem — see _device_queryset).
DEVICES_PER_PAGE = 25

# Distinct search-input name so the person picker cannot collide with the device
# form's own fields, and a cap so the "*" / live-search dropdown stays usable.
PERSON_SEARCH_PARAM = "q_person"
PERSON_SEARCH_LIMIT = 25


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

    page_obj = paginate(request, device_filter.qs, DEVICES_PER_PAGE)

    context = {
        "filter": device_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            device_filter,
            request,
            target="#device-list",
            search_placeholder=_("Search IT ID, serial number, model..."),
            secondary_fields={"is_imported", "duplicate", "active_record__inventory"},
        ),
        "current_ordering": data["ordering"],
        # paginator.count runs the filtered COUNT once; reuse it here instead of
        # a second device_filter.qs.count().
        "device_filtered_count": page_obj.paginator.count,
        "device_total_count": base_queryset.count(),
        # The Modified column shows relative time ("2 hours ago") only for recent
        # edits; anything older than this cutoff falls back to an absolute date.
        # Mirrors dlcdb.lending.views.index.
        "recent_cutoff": timezone.now() - datetime.timedelta(weeks=3),
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

    # The index threads its active search/filter/sort here as ?next= so Save,
    # Back and Cancel return to the exact filtered list. Read from GET so it
    # survives both the render and the POST (form_action carries it forward).
    next_query = request.GET.get("next", "")
    index_url = reverse("assets:device_index")
    if next_query:
        index_url = f"{index_url}?{next_query}"
    form_action = reverse("assets:device_detail", args=[device.pk])
    if next_query:
        form_action += "?" + urlencode({"next": next_query})

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied
        form = DeviceForm(request.POST, instance=device, request=request)
        if form.is_valid():
            saved_device = form.save(commit=False)
            if not request.user.is_superuser:
                saved_device.tenant = getattr(request, "tenant", None)
            saved_device.user, saved_device.username = get_denormalized_user(request.user)
            saved_device.save()
            messages.success(request, _("Device “%(device)s” was updated.") % {"device": saved_device})
            return redirect(index_url)
    else:
        form = DeviceForm(instance=device, request=request)

    return TemplateResponse(
        request,
        "assets/devices/detail.html",
        {
            "device": device,
            "form": form,
            "can_change": can_change,
            "index_url": index_url,
            "form_action": form_action,
            # Shared state-machine data (same builder the admin uses); the
            # "assets" surface swaps in native frontend URLs for Move/Lend.
            "state_data": device.get_state_data(user=request.user, app_name="assets"),
        },
    )


@require_POST
@htmx_login_required
@htmx_permission_required("core.change_device")
def person_search(request):
    """
    HTMX live-search backing the contact-person picker on the device form. An
    empty query returns nothing (so the picker starts blank); "*" lists everyone
    (capped). Mirrors ``relocate.room_search``.
    """
    value = (request.POST.get(PERSON_SEARCH_PARAM) or "").strip()
    people = Person.objects.all()

    if not value:
        people = people.none()
    elif value != "*":
        people = people.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value) | Q(email__icontains=value)
        )

    people = people.order_by("last_name", "first_name")[:PERSON_SEARCH_LIMIT]
    return TemplateResponse(
        request,
        "assets/includes/_person_search_results.html",
        {"people": people, "query": value},
    )
