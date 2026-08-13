# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The record trail: the non-admin counterpart of the Record changelist.

Records are the app's event log — one row per device state change, written only
by the lifecycle transitions. This frontend is therefore purely read-only: two
GET views, no forms, no POST branches, no add/change/delete routes, for every
user including superusers.

Reached either as the whole trail (``/assets/records/``) or scoped to one device
(``?device=<pk>``), which is how the device sidebar links here.
"""

from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _

from dlcdb.core.models import Device, Record
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.lifecycle_display import active_record_color_case
from dlcdb.theme.pagination import paginate

from ..filters import RecordFilter

RECORDS_PER_PAGE = 25

# A trail is an append-only event log, so creation time is the event time.
# modified_at moves when a record is superseded, which would reshuffle history.
# Set as a default on the incoming data rather than on the FilterSet so an
# explicit ?ordering= — a column header, the sort dropdown — still wins. The
# value is RecordFilter's public alias, not the model field: anything else is
# not a valid choice and silently leaves the queryset unordered.
DEFAULT_ORDERING = "-created"


def _record_queryset(request):
    """Records visible in the frontend, with every relation a row renders."""
    queryset = Record.objects.select_related(
        "device",
        "device__device_type",
        "room",
        "person",
        "inventory",
        "user",
    ).annotate(state_color=active_record_color_case(field="record_type"))
    return tenant_scoped_queryset(queryset, request, tenant_field="device__tenant")


def _scope_device(request):
    """The device named by ``?device=<pk>``, or None.

    The scope narrows the base queryset before the FilterSet, so the "x of y"
    line and the "Clear all" reset both speak about this one device's records
    rather than about all of them. Non-numeric input is ignored rather than
    fatal (get_object_or_404 raises ValueError, not Http404, on a bad pk); an
    unknown or out-of-tenant device is a 404, same as the device page itself.
    """
    value = request.GET.get("device", "")
    if not value.isdigit():
        return None
    devices = tenant_scoped_queryset(Device.objects.all(), request, tenant_field="tenant")
    return get_object_or_404(devices, pk=value)


@permission_required("core.view_record", raise_exception=True)
def record_index(request):
    """The record trail, optionally scoped to one device, with HTMX filtering."""
    template = "assets/records/index.html#record-list" if request.htmx else "assets/records/index.html"

    device = _scope_device(request)
    queryset = _record_queryset(request)
    if device:
        queryset = queryset.filter(device=device)

    data = request.GET.copy()
    data.setdefault("ordering", DEFAULT_ORDERING)
    record_filter = RecordFilter(data, queryset=queryset, request=request)

    page_obj = paginate(request, record_filter.qs, RECORDS_PER_PAGE)

    context = {
        "filter": record_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            record_filter,
            request,
            target="#record-list",
            search_placeholder=_("Search IT ID, inventory ID, serial number, person, room, note..."),
            secondary_fields={"inventory", "device__manufacturer", "disposition_state"},
            # The bar is a GET form: without a hidden input the device scope
            # would be dropped by the first keystroke. .pk, not the object —
            # the input value is rendered verbatim.
            hidden_params={"device": device.pk} if device else None,
        ),
        "current_ordering": record_filter.data["ordering"],
        # paginator.count runs the filtered COUNT once; reuse it here instead of
        # a second record_filter.qs.count().
        "record_filtered_count": page_obj.paginator.count,
        "record_total_count": record_filter.queryset.count(),
        "scope_device": device,
    }
    return TemplateResponse(request, template, context)


@permission_required("core.view_record", raise_exception=True)
def record_detail(request, pk):
    """One record, read only: no form, no POST branch, nothing to save."""
    record = get_object_or_404(
        _record_queryset(request)
        .select_related("device__manufacturer", "assigned_device")
        .prefetch_related("attachments"),
        pk=pk,
    )

    # The index threads its active search/filter/sort here as ?next= so Back
    # returns to the exact filtered list. Same idiom as device_detail.
    next_query = request.GET.get("next", "")
    index_url = reverse("assets:record_index")
    if next_query:
        index_url = f"{index_url}?{next_query}"

    return TemplateResponse(
        request,
        "assets/records/detail.html",
        {
            "record": record,
            "index_url": index_url,
            # Closes the loop device -> trail -> one record -> that device's trail.
            "device_records_url": f"{reverse('assets:record_index')}?device={record.device_id}",
        },
    )
