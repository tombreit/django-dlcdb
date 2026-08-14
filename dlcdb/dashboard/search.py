# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Global search: one term, matched across every kind of object the frontend has a
detail page for.

The per-model list views each own a good free-text search already (a
``django_filters.FilterSet`` with a ``search`` field). This module does not
re-implement any of them: every source below binds the *owning app's own*
FilterSet with nothing but the term, so "what counts as a match" can never drift
between the global search and the list it links to.

Shape follows ``dlcdb.assets.views.masterdata``: a frozen spec per surface plus
one generic implementation. Deliberately *not* a registry like
``dlcdb.theme.pickers`` -- that one exists to break an import cycle, because
``theme`` sits below the feature apps and must not import their models. The
dashboard sits on top (it already imports core models and reverses assets/
lending/licenses/smallstuff URL names), so a plain module-level tuple costs
nothing and hides nothing.
"""

from dataclasses import dataclass
from typing import Callable

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from dlcdb.assets.filters import DeviceFilter
from dlcdb.core.models import Device, LentRecord, Person, Room
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.lending.filters import LentRecordFilter
from dlcdb.persons.filters import PersonFilter
from dlcdb.rooms.filters import RoomFilter
from dlcdb.smallstuff.models import AssignedThing
from dlcdb.theme.lifecycle_display import active_record_color_case

# Rows shown per group before the "show all" link takes over. The global search
# is triage; the per-model list view is the full result set.
RESULTS_PER_SOURCE = 8

# Below this many characters nothing is searched at all, so a single keystroke
# never scans every table.
MIN_TERM_LENGTH = 2


@dataclass(frozen=True)
class SearchSource:
    """One searchable kind of object: where to look, who may look, where results lead."""

    key: str  # stable slug, also the group's DOM id
    label: str  # translated plural heading; NOT taken from Model._meta (see below)
    icon: str  # Bootstrap icon class
    # The permissions that reveal this group, any one of which suffices -- same
    # any-of semantics as theme.pickers.PickerSource. These are the permissions
    # the *result link target* needs, not the ones its list view needs, so a
    # result row can never lead to a 403.
    permissions: tuple[str, ...]
    get_queryset: Callable[[HttpRequest], QuerySet]  # base qs, tenant scoping included
    search: Callable[[QuerySet, str, HttpRequest], QuerySet]
    row_template: str
    index_url: str  # URL name of the list view behind "show all"
    # GET parameter that list view reads the term from. Empty when the target
    # cannot be prefilled at all (smallstuff searches over POST), in which case
    # "show all" is a plain link to the unfiltered list.
    index_param: str = "search"

    def grants_access(self, user) -> bool:
        """True if ``user`` holds any of this source's permissions."""
        return any(user.has_perm(permission) for permission in self.permissions)


def _filtered(filter_class, queryset, term, request):
    """Run one FilterSet's ``search`` over ``queryset``.

    Only ``search`` is bound, so every other filter is empty and a no-op. The
    ``OrderingFilter`` stays unbound too, which leaves the queryset on its
    model's ``Meta.ordering`` -- deterministic for every model used here, so the
    slice below is stable. Note this is the opposite of what a filterbar page
    must do (those seed a default ordering); this page has no filterbar.
    """
    return filter_class({"search": term}, queryset=queryset, request=request).qs


# --- Devices ---------------------------------------------------------------
# Licences are devices too, but they get their own group (and their own detail
# page), so they are excluded here to keep a licence out of two groups at once.


def _device_queryset(request):
    queryset = Device.objects.exclude(is_licence=True).select_related(
        "active_record__room",
        "active_record__person",
        "device_type",
        "manufacturer",
    )
    return tenant_scoped_queryset(
        queryset.annotate(state_color=active_record_color_case()), request, tenant_field="tenant"
    )


# --- Licences --------------------------------------------------------------
# Searched as Devices, not as LicenceRecords, for three reasons:
#   * ``licenses:edit`` is routed ``<int:license_id>`` and resolves a *Device*,
#     so a device pk is all a link needs (and Device.get_absolute_url() already
#     routes licence devices there);
#   * LicenceRecordFilter.search matches on ``device_human_title``, an
#     annotation only the licenses index view supplies;
#   * LicenceRecord.objects annotates a correlated subscriber StringAgg
#     subquery per row -- far too heavy for a keystroke-debounced endpoint.


def _licence_queryset(request):
    queryset = Device.objects.filter(is_licence=True).select_related(
        "device_type",
        "manufacturer",
        "supplier",
    )
    return tenant_scoped_queryset(queryset, request, tenant_field="tenant")


# --- Persons, rooms --------------------------------------------------------
# Neither model carries a tenant, and neither of their own index views scopes by
# one; scoping them here would show non-superusers nothing at all.


def _person_queryset(request):
    return Person.objects.select_related("organizational_unit")


def _room_queryset(request):
    return Room.objects.all()


# --- Lendings --------------------------------------------------------------


def _lending_queryset(request):
    queryset = LentRecord.objects.select_related("device", "device__manufacturer", "person", "room")
    return tenant_scoped_queryset(queryset, request, tenant_field="device__tenant")


# --- Smallstuff ------------------------------------------------------------
# The only source without a reusable FilterSet: smallstuff's own PersonFilter
# discards the queryset it is handed and rebuilds from a different manager, so
# it cannot be pointed at anything. Rows are assignments; they link to the
# person's detail page, the only smallstuff frontend detail view there is.


def _smallstuff_queryset(request):
    return AssignedThing.currently_assigned_objects.select_related("person", "thing")


def _smallstuff_search(queryset, term, request):
    return queryset.filter(
        Q(thing__name__icontains=term)
        | Q(person__first_name__icontains=term)
        | Q(person__last_name__icontains=term)
        | Q(person__email__icontains=term)
    )


# Declaration order is display order: the groups appear on the dashboard exactly
# as listed here, most operationally urgent first.
SEARCH_SOURCES = (
    SearchSource(
        key="lendings",
        label=_("Lendings"),
        icon="bi bi-arrow-left-right",
        permissions=("core.view_lentrecord",),
        get_queryset=_lending_queryset,
        search=lambda qs, term, request: _filtered(LentRecordFilter, qs, term, request),
        row_template="dashboard/search/_row_lending.html",
        index_url="lending:index",
    ),
    SearchSource(
        key="devices",
        label=_("Devices"),
        icon="bi bi-upc",
        permissions=("core.view_device",),
        get_queryset=_device_queryset,
        search=lambda qs, term, request: _filtered(DeviceFilter, qs, term, request),
        row_template="dashboard/search/_row_device.html",
        index_url="assets:device_index",
    ),
    SearchSource(
        key="licenses",
        label=_("Licenses"),
        icon="bi bi-bank2",
        # licenses:index is login-only, but licenses:edit -- where these rows
        # lead -- needs the change permission.
        permissions=("core.change_licencerecord",),
        get_queryset=_licence_queryset,
        search=lambda qs, term, request: _filtered(DeviceFilter, qs, term, request),
        row_template="dashboard/search/_row_license.html",
        index_url="licenses:index",
    ),
    SearchSource(
        key="persons",
        # Explicit label: Person._meta.verbose_name_plural is the hardcoded,
        # untranslated German string "Personen".
        label=_("Persons"),
        icon="bi bi-person",
        permissions=("core.view_person",),
        get_queryset=_person_queryset,
        search=lambda qs, term, request: _filtered(PersonFilter, qs, term, request),
        row_template="dashboard/search/_row_person.html",
        index_url="persons:index",
    ),
    SearchSource(
        key="rooms",
        label=_("Rooms"),
        icon="bi bi-door-open",
        permissions=("core.view_room",),
        get_queryset=_room_queryset,
        search=lambda qs, term, request: _filtered(RoomFilter, qs, term, request),
        row_template="dashboard/search/_row_room.html",
        index_url="rooms:index",
    ),
    SearchSource(
        key="smallstuff",
        label=_("Smallstuff"),
        icon="bi bi-handbag",
        # The nav entry uses view_assignedthing, but smallstuff:person_detail
        # requires change_assignedthing.
        permissions=("smallstuff.change_assignedthing",),
        get_queryset=_smallstuff_queryset,
        search=_smallstuff_search,
        row_template="dashboard/search/_row_smallstuff.html",
        index_url="smallstuff:person_search",
        # That view reads its term from POST, so a ?search= would be ignored.
        index_param="",
    ),
)


def run_search(request, term):
    """Search every source the user may see; return one group per non-empty result.

    Two queries per permitted source (a COUNT and a LIMIT), so at most a dozen
    for a fully privileged user -- acceptable for an endpoint the client
    debounces. If it ever stops being acceptable, drop the COUNT and fetch
    ``RESULTS_PER_SOURCE + 1`` rows to render "8+" instead of an exact total.
    """
    term = (term or "").strip()
    if len(term) < MIN_TERM_LENGTH:
        return []

    groups = []
    for source in SEARCH_SOURCES:
        if not source.grants_access(request.user):
            continue

        results = source.search(source.get_queryset(request), term, request)
        total = results.count()
        if not total:
            continue

        # Deep link into the model's own list with the same term prefilled --
        # that list is the full result set.
        show_all_href = reverse(source.index_url)
        if source.index_param:
            show_all_href += f"?{urlencode({source.index_param: term})}"

        groups.append(
            {
                "source": source,
                "rows": results[:RESULTS_PER_SOURCE],
                "total": total,
                "has_more": total > RESULTS_PER_SOURCE,
                "show_all_href": show_all_href,
            }
        )

    return groups
