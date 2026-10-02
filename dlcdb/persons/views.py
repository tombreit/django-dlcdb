# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The standalone Person frontend: list, add and edit persons outside the admin."""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _

from dlcdb.core.models import Person, Record
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.tenants.shortcuts import tenant_scoped_queryset
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.navigation import detail_urls
from dlcdb.theme.pagination import paginate

from .assignments import group_assignments
from .filters import PersonFilter
from .forms import PersonForm

PERSONS_PER_PAGE = 25


def _person_queryset():
    """Persons visible in the frontend (the default manager excludes soft-deleted)."""
    return Person.objects.select_related("organizational_unit")


def _person_records(request, person):
    """
    The person's device records in the user's tenants: lendings and licence
    assignments. Plain ``Record`` rather than the LentRecord/LicenceRecord
    proxies, whose managers hide inactive records -- and the inactive ones are
    the person's history. See ``assignments`` for why one assignment can span
    several records.
    """
    queryset = person.record_set.select_related("device", "device__device_type", "device__manufacturer", "room")
    return tenant_scoped_queryset(queryset, request, tenant_field="device__tenant")


@permission_required("core.view_person", raise_exception=True)
def person_index(request):
    """Person overview, with progressive HTMX filtering."""
    template = "persons/index.html#person-list" if request.htmx else "persons/index.html"
    base_queryset = _person_queryset()

    data = request.GET.copy()
    data.setdefault("ordering", "name")
    person_filter = PersonFilter(data, queryset=base_queryset, request=request)

    page_obj = paginate(request, person_filter.qs, PERSONS_PER_PAGE)

    context = {
        "filter": person_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            person_filter,
            request,
            target="#person-list",
            search_placeholder=_("Search name or e-mail..."),
        ),
        "current_ordering": data["ordering"],
        "filtered_count": page_obj.paginator.count,
        "total_count": base_queryset.count(),
    }
    return TemplateResponse(request, template, context)


@permission_required("core.add_person", raise_exception=True)
def person_add(request):
    """Create a DLCDB-owned person and attach the audit information."""
    form = PersonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        person = form.save(commit=False)
        person.user, person.username = get_denormalized_user(request.user)
        person.save()
        messages.success(request, _("Person “%(person)s” was created.") % {"person": person})
        return redirect("persons:detail", pk=person.pk)

    return TemplateResponse(
        request,
        "persons/form.html",
        {"form": form, "title": _("Add person"), "submit_label": _("Create person")},
    )


@permission_required("core.view_person", raise_exception=True)
def person_detail(request, pk):
    """
    Read and edit one person in the same page. A person matched with a UDB
    person (``udb_person_uuid`` set) is managed by the UDB sync and therefore
    read-only here — enforced server-side, not just by hiding the form.
    """
    person = get_object_or_404(_person_queryset(), pk=pk)
    is_udb_synced = bool(person.udb_person_uuid)
    can_change = request.user.has_perm("core.change_person") and not is_udb_synced

    # The index threads its active search/filter/sort here as ?next= so Save,
    # Back and Cancel return to the exact filtered list.
    index_url, form_action = detail_urls(request, "persons:index", "persons:detail", person.pk)

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            saved_person = form.save(commit=False)
            saved_person.user, saved_person.username = get_denormalized_user(request.user)
            saved_person.save()
            messages.success(request, _("Person “%(person)s” was updated.") % {"person": saved_person})
            return redirect(index_url)
    else:
        form = PersonForm(instance=person)

    # What is or was assigned to the person, current first. The template shows
    # each card only with the matching view permission.
    records = _person_records(request, person)
    lendings = group_assignments(records.filter(record_type=Record.LENT))
    # A lent licence is listed once, as a lending.
    licences = group_assignments(records.filter(device__is_licence=True).exclude(record_type=Record.LENT))
    # Still issued (no return date) first, then by most recent return.
    assigned_things = person.assignedthing_set.select_related("thing").order_by(
        F("unassigned_at").desc(nulls_first=True), "-assigned_at"
    )

    return TemplateResponse(
        request,
        "persons/detail.html",
        {
            "person": person,
            "form": form,
            "can_change": can_change,
            "is_udb_synced": is_udb_synced,
            "index_url": index_url,
            "form_action": form_action,
            "lendings": lendings,
            "licences": licences,
            "assigned_things": assigned_things,
        },
    )
