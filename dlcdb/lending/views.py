# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BooleanField, Case, CharField, Count, IntegerField, Q, Value, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core import lifecycle
from dlcdb.core.models import LentRecord, Person, Record, Room
from dlcdb.theme.lifecycle_display import STATE_COLORS
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.core.utils.links import linked_message
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.dataexchange.csv_export import (
    LENDING_EXPORT_RELATIONS,
    csv_response,
    lending_export_columns,
)
from dlcdb.theme.export import export_href
from dlcdb.theme.filterbar import build_filterbar

from .decorators import htmx_permission_required
from .filters import (
    LendingPersonFilter,
    LentRecordFilter,
    STATE_OVERDUE,
    STATE_LENT,
    STATE_AVAILABLE,
)
from .forms import LendableDeviceSelectForm, LendingForm, LendingReturnForm
from .models import LendingConfiguration, LendingProfile


# Applied when the request names no ordering; an explicit ?ordering= still wins.
DEFAULT_ORDERING = "-modified"


def _tenant_scoped(queryset, request):
    """
    Scope a record queryset to the current tenant via the related device.
    Records carry no tenant field of their own; the shared policy lives in
    ``dlcdb.core.utils.tenants``.
    """
    return tenant_scoped_queryset(queryset, request, tenant_field="device__tenant")


def _annotate_lent_state(queryset):
    """
    Annotate each record with a display state, a matching Bootstrap contextual
    color and a sort weight (most urgent first). Whether overdue lendings are
    highlighted is controlled by LendingConfiguration.admin_mark_overdue.
    """
    today = datetime.date.today()
    mark_overdue = LendingConfiguration.load().admin_mark_overdue
    overdue = Q(lent_desired_end_date__lte=today) & Q(lent_end_date__isnull=True)

    state_whens, color_whens, sort_whens = [], [], []

    if mark_overdue:
        state_whens.append(When(overdue, then=Value(STATE_OVERDUE)))
        color_whens.append(When(overdue, then=Value("danger")))
        # Available first, then overdue at the top of the lent group, then lent.
        sort_whens.append(When(overdue, then=Value(2)))

    state_whens += [
        When(record_type=Record.LENT, then=Value(STATE_LENT)),
        When(record_type=Record.INROOM, then=Value(STATE_AVAILABLE)),
    ]
    # Derive badge colours from the single state→colour map (theme.lifecycle_display)
    # so the lending list and the asset card cannot disagree.
    color_whens += [
        When(record_type=Record.LENT, then=Value(STATE_COLORS[Record.LENT])),
        When(record_type=Record.INROOM, then=Value(STATE_COLORS[Record.INROOM])),
    ]
    sort_whens += [
        When(record_type=Record.INROOM, then=Value(1)),
        When(record_type=Record.LENT, then=Value(3)),
    ]

    return queryset.annotate(
        lent_state=Case(*state_whens, default=Value("unknown"), output_field=CharField()),
        lent_state_color=Case(*color_whens, default=Value("secondary"), output_field=CharField()),
        lent_state_sort=Case(*sort_whens, default=Value(9), output_field=IntegerField()),
        # Always computed, independent of admin_mark_overdue, so the due-date
        # column can flag genuinely overdue lendings.
        is_overdue=Case(When(overdue, then=Value(True)), default=Value(False), output_field=BooleanField()),
    ).order_by("lent_state_sort", "device__edv_id")


def _lending_filter(request):
    """The bound ``LentRecordFilter`` this request's GET parameters select.

    Shared by the index and the CSV export, so a download can never disagree
    with the list it was started from: same tenant scoping, same annotations,
    same filters, same ordering. ``.qs`` is the filtered queryset, ``.queryset``
    the unfiltered one.
    """
    base_qs = _annotate_lent_state(
        _tenant_scoped(
            LentRecord.objects.select_related("device__manufacturer", "device__device_type", "person", "room"),
            request,
        )
    )

    # Default the list to newest-modified first. Copying request.GET (immutable)
    # and using setdefault means the OrderingFilter always applies an ordering,
    # so the default view is modified-desc while explicit clicks still win.
    data = request.GET.copy()
    data.setdefault("ordering", DEFAULT_ORDERING)

    return LentRecordFilter(data, queryset=base_qs, request=request)


@login_required
@permission_required("core.view_lentrecord", raise_exception=True)
def index(request):
    """
    Overview of lendable devices: what is currently lent to whom and what is
    available, with live HTMX search/filtering and bookmarkable URLs.
    """
    template = "lending/index.html#lent-list" if request.htmx else "lending/index.html"

    lent_record_filter = _lending_filter(request)

    counts = lent_record_filter.qs.aggregate(
        total=Count("pk"),
        available=Count("pk", filter=Q(record_type=Record.INROOM)),
        lent=Count("pk", filter=Q(record_type=Record.LENT)),
    )

    context = {
        "filter": lent_record_filter,
        "filterbar": build_filterbar(
            lent_record_filter,
            request,
            target="#lent-list",
            search_placeholder=_("Search device, person, note..."),
        ),
        "current_ordering": lent_record_filter.data.get("ordering"),
        # The Modified column shows relative time ("2 hours ago") only for recent
        # edits; anything older than this cutoff falls back to an absolute date.
        "recent_cutoff": timezone.now() - datetime.timedelta(weeks=3),
        "lent_filtered_count": counts["total"],
        "lent_total_count": lent_record_filter.queryset.count(),
        "lent_available_count": counts["available"],
        "lent_lent_count": counts["lent"],
        # No pagination on this page, so the export covers exactly what is shown.
        "export_href": export_href(request, "lending:export_csv", drop=()),
    }

    return TemplateResponse(request, template, context)


@login_required
@permission_required("core.view_lentrecord", raise_exception=True)
def lending_export_csv(request):
    """The current lending list as a CSV download.

    Every row the active search, filters and ordering select. This page is
    unpaginated, so that is exactly what is on screen. Shares ``_lending_filter``
    with the index so the two cannot drift apart.

    Lending-shaped columns rather than the device set: on this page the borrower,
    their email and the loan's reason and accessories are the point.
    """
    return csv_response(
        _lending_filter(request).qs.select_related(*LENDING_EXPORT_RELATIONS),
        columns=lending_export_columns(),
        slug="core-lentrecord",
    )


def _get_scoped_record(request, pk):
    """
    Fetch the lending record for ``pk``, scoped to the request's tenant so a
    user can only open rows they can also see on the index. Returns a 404 for
    out-of-tenant or non-lentable (e.g. REMOVED) records.
    """
    return get_object_or_404(
        _tenant_scoped(
            LentRecord.objects.select_related("device__active_record__room", "person", "room"),
            request,
        ),
        pk=pk,
    )


def _get_scoped_inroom_record(request, device_pk):
    """
    Resolve a device pk (as chosen in the device picker) to its current,
    tenant-visible INROOM record — the available record a new lending starts
    from. ``LentRecord.objects`` already restricts to the active record, so there
    is at most one. Returns ``None`` if the device is out of tenant, unknown, or
    no longer available (so the caller can reject it).
    """
    record = (
        _tenant_scoped(LentRecord.objects.select_related("device", "person", "room"), request)
        .filter(device_id=device_pk)
        .first()
    )
    if record is None or record.record_type != Record.INROOM:
        return None
    return record


def _lending_soft_warnings(request, form):
    """
    Non-blocking warnings mirroring ``LentRecordAdmin.save_model``: flag a
    missing UDB contract end date and a desired return date that runs past it.
    """
    person = form.cleaned_data.get("person")
    desired_end = form.cleaned_data.get("lent_desired_end_date")
    if not person:
        return

    contract_end = person.udb_contract_planned_checkout
    if not contract_end:
        messages.warning(request, _("Warning: No HR contract end date found for %(person)s!") % {"person": person})
    elif desired_end and desired_end > contract_end:
        messages.warning(request, _("Warning: Contract ends before the desired return date!"))


def _apply_state_machine(record, form, user, username):
    """
    Dispatch a lend/return/edit to the lifecycle transitions:

    - INROOM (available) -> ``transition_lend`` (append a new LENT record).
    - LENT + return date -> ``transition_return_lending`` (stamp the return, then
      auto-return the device to its room).
    - LENT, no return date -> a plain in-place save of the edited LENT record
      (editing a lending is not a transition).
    """
    obj = form.save(commit=False)

    if record.record_type == Record.LENT and obj.lent_end_date:
        lifecycle.transition_return_lending(obj, user=user, lent_end_date=obj.lent_end_date)

    elif record.record_type == Record.LENT:
        obj.user, obj.username = user, username
        obj.save()

    elif record.record_type == Record.INROOM:
        lifecycle.transition_lend(
            record.device,
            person=form.cleaned_data["person"],
            room=form.cleaned_data["room"],
            lent_start_date=form.cleaned_data["lent_start_date"],
            lent_desired_end_date=form.cleaned_data["lent_desired_end_date"],
            sync_lent_end_date=form.cleaned_data.get("sync_lent_end_date", False),
            lent_note=form.cleaned_data.get("lent_note", ""),
            lent_reason=form.cleaned_data.get("lent_reason", ""),
            lent_accessories=form.cleaned_data.get("lent_accessories", ""),
            user=user,
        )

    else:
        raise ValidationError(_("Lent state unknown - please report this issue!"))


def _save_lending(request, record, form):
    """
    Run the soft warnings and the lend/return/edit state machine in one
    transaction. Returns True on success (caller should redirect) or False if a
    form error was added (caller should re-render). Shared by all three flows of
    ``lend``.
    """
    user, username = get_denormalized_user(request.user)
    # Soft warnings sanity-check a lending's dates against the borrower's contract;
    # they do not apply when the submit is acknowledging a return (lent_end_date set).
    if not form.cleaned_data.get("lent_end_date"):
        _lending_soft_warnings(request, form)
    try:
        with transaction.atomic():
            _apply_state_machine(record, form, user, username)
    except Room.DoesNotExist as exc:
        messages.error(request, _("Configuration error: %(err)s") % {"err": exc})
        return False
    except ValidationError as exc:
        form.add_error(None, exc)
        return False

    if record.record_type == Record.INROOM:
        msg = _("Device “{device}” lent to “{person}”.")
    elif record.lent_end_date or form.cleaned_data.get("lent_end_date"):
        msg = _("Return of “{device}” from “{person}” acknowledged.")
    else:
        msg = _("Lending of “{device}” to “{person}” saved.")
    messages.success(
        request,
        # The return form does not carry the borrower (it cannot be changed while
        # returning), so fall back to the one stored on the record.
        linked_message(msg, device=record.device, person=form.cleaned_data.get("person") or record.person),
    )
    return True


@login_required
@htmx_permission_required(lifecycle.BY_NAME["lend"].permission)
def lend(request, pk=None):
    """
    Single lending screen. Two entry points share one form and one save path:

    - **picker mode** (``pk`` is None, ``lending:lend``): pick an available device
      via the live device picker and a person, then lend in one submit.
    - **record mode** (``pk`` given, ``lending:detail``): open a device's active
      ``LentRecord`` to lend it (INROOM), or -- for a LENT one -- to acknowledge
      its return (``?flow=return``, ``LendingReturnForm``) or to edit the lending
      without ending it (no querystring, ``LendingForm``). The device is shown
      locked in both.

    Both resolve to a ``LentRecord`` and run the same ``_save_lending`` state
    machine. Replaces the django-admin LentRecord change view.
    """
    picker_mode = pk is None
    device_form = LendableDeviceSelectForm(request.POST or None, request=request) if picker_mode else None

    # Filters/search on the index live in its querystring; the row links carry it
    # here as ?next=. Thread it back into the post-save redirect and the
    # back/cancel links so the user returns to the exact filtered view. Read from
    # request.GET so it works on both the GET render and the POST (form_action
    # carries it in its querystring).
    index_query = request.GET.get("next", "")
    index_url = reverse("lending:index")
    if index_query:
        index_url = f"{index_url}?{index_query}"

    if picker_mode:
        record = device = None
    else:
        record = _get_scoped_record(request, pk)
        device = record.device
        if record.record_type == Record.LOST:
            messages.error(request, _('Device is currently "not locatable" and must be located first.'))
            return redirect(index_url)

    # The three flows of this screen, resolved once. A LENT record is "returned"
    # only when the user asked for it via ?flow=return (the Return button in the
    # list and on the device card); without it, opening a lending just edits it.
    # Read from request.GET so the flow survives the POST, which form_action
    # carries it in.
    is_lend_flow = picker_mode or record.record_type == Record.INROOM
    is_return_flow = not is_lend_flow and request.GET.get("flow") == "return"
    is_edit_flow = not is_lend_flow and not is_return_flow

    # Returning ends the lending, lending and editing do not: two disjoint forms
    # over the same record, so neither flow can perform the other's write.
    form_class = LendingReturnForm if is_return_flow else LendingForm

    if request.method == "POST":
        if picker_mode:
            device_pk = request.POST.get("device")
            if not device_pk:
                messages.error(request, _("Please select a device to lend."))
                return redirect("lending:lend")
            record = _get_scoped_inroom_record(request, device_pk)
            if record is None:
                messages.error(request, _("This device is no longer available for lending."))
                return redirect("lending:lend")
            device = record.device

        form_kwargs = {} if is_return_flow else {"record_type": record.record_type}
        form = form_class(request.POST, instance=record, **form_kwargs)
        if form.is_valid() and _save_lending(request, record, form):
            return redirect(index_url)
    else:
        form_kwargs = {} if is_return_flow else {"record_type": record.record_type if record else Record.INROOM}
        form = form_class(instance=record, **form_kwargs)

    # Keep the visually selected person card in sync after a failed POST, where
    # the picked person lives only in the submitted (hidden) person field. In
    # record mode it defaults to the record's current person.
    selected_person = record.person if record else None
    if request.method == "POST":
        submitted_person_id = request.POST.get("person")
        if submitted_person_id:
            selected_person = Person.objects.filter(pk=submitted_person_id).first() or selected_person

    # A slip needs a device type whose profile carries a slip template — an empty
    # one is rejected by the database template loader (see loader.py). Independent
    # of the record type: print_sheet renders the submitted form data for an
    # available device and for an active lending alike. In picker mode the device
    # is chosen client-side, so the button renders disabled and the inline JS
    # enables it once a device is set.
    can_print_slip = picker_mode or (
        LendingProfile.objects.exclude(lent_sheet_template="").filter(device_type=device.device_type).exists()
    )

    # Carry the flow and the index filters through the POST (and any failed-POST
    # re-render) by appending them to the form action: ?flow= decides which form
    # the POST is bound to, ?next= where the save redirects to.
    form_action = reverse("lending:lend") if picker_mode else reverse("lending:detail", args=[record.pk])
    form_action_query = {}
    if is_return_flow:
        form_action_query["flow"] = "return"
    if index_query:
        form_action_query["next"] = index_query
    if form_action_query:
        form_action += "?" + urlencode(form_action_query)

    # Same route without the flow marker: where the return screen sends a user
    # who wants to change the lending itself rather than end it.
    edit_url = None if picker_mode else reverse("lending:detail", args=[record.pk])
    if edit_url and index_query:
        edit_url += "?" + urlencode({"next": index_query})

    # Target of the "Return device" button on the edit screen: this same record
    # with ?flow=return. Only an active lending can be returned, so it stays None
    # in the other flows and the button is not rendered there.
    return_url = None
    if is_edit_flow:
        return_query = {"flow": "return"}
        if index_query:
            return_query["next"] = index_query
        return_url = f"{reverse('lending:detail', args=[record.pk])}?{urlencode(return_query)}"

    context = {
        "form": form,
        "device_form": device_form,
        "record": record,
        "device": device,
        "selected_person": selected_person,
        "picker_mode": picker_mode,
        "is_lend_flow": is_lend_flow,
        "is_return_flow": is_return_flow,
        "is_edit_flow": is_edit_flow,
        "title": _("Return device")
        if is_return_flow
        else (
            _("Lend") if picker_mode else (_("Lend device") if record.record_type == Record.INROOM else _("Lending"))
        ),
        "obj_admin_url": None if picker_mode else reverse("admin:core_lentrecord_change", args=[record.pk]),
        "can_print_slip": can_print_slip,
        "form_action": form_action,
        "edit_url": edit_url,
        "return_url": return_url,
        "index_url": index_url,
    }
    return TemplateResponse(request, "lending/lend.html", context)


@login_required
@htmx_permission_required(lifecycle.BY_NAME["lend"].permission)
def person_search(request):
    """HTMX live-search backing the person picker on the detail view."""
    # Start from an empty queryset: django-filter skips empty filter values, so
    # a blank search box must yield no people rather than the whole directory.
    person_filter = LendingPersonFilter(request.POST or None, queryset=Person.objects.none())
    return TemplateResponse(
        request,
        "lending/includes/_person_search_results.html",
        {"filter": person_filter},
    )


def _build_unsaved_lentrecord(device, form):
    """
    Construct an unsaved LentRecord from (possibly partial) form data, falling
    back to the record the form was bound to. The fallback carries the reprint of
    an active lending: the return screen submits only the return fields, so
    everything the slip shows about the lending itself comes from the record.
    """
    record = form.instance
    person_id = form.data.get("person")
    person = Person.objects.filter(pk=person_id).first() if person_id else record.person
    return LentRecord(
        device=device,
        person=person,
        room=form.cleaned_data.get("room") or record.room,
        lent_start_date=form.cleaned_data.get("lent_start_date") or record.lent_start_date,
        lent_desired_end_date=form.cleaned_data.get("lent_desired_end_date") or record.lent_desired_end_date,
        lent_accessories=form.data.get("lent_accessories", record.lent_accessories),
        lent_note=form.data.get("lent_note", record.lent_note),
        lent_reason=form.data.get("lent_reason", record.lent_reason),
    )


@login_required
@htmx_permission_required(lifecycle.BY_NAME["lend"].permission)
@require_POST
def print_sheet(request, pk):
    """
    Render the "Ausleihzettel" (lending slip) from the *unsaved* form data, so
    helpdesk can print and have it signed before committing the lending — and so
    an active lending can be reprinted with the edits currently on screen.
    Generalizes ``print_lent_sheet`` (below), which renders a saved record.

    ``pk`` is the device pk (the device picker's option id); the slip is built
    from the device's current record plus the submitted form data.
    """
    # The device's current, tenant-visible record — INROOM (about to be lent) or
    # LENT (reprint for an active lending). LOST must be located first.
    record = (
        _tenant_scoped(LentRecord.objects.select_related("device", "person", "room"), request)
        .filter(device_id=pk)
        .first()
    )
    if record is None or record.record_type == Record.LOST:
        raise Http404("No printable lending record for this device.")
    device = record.device

    form = LendingForm(request.POST, instance=record, record_type=record.record_type)
    # Populate cleaned_data without hard-blocking on validation: a slip should
    # print even from a partially filled form.
    form.is_valid()

    unsaved_record = _build_unsaved_lentrecord(device, form)

    device_type = device.device_type
    if not device_type:
        raise Http404("Device has no device type assigned.")

    try:
        profile = LendingProfile.objects.exclude(lent_sheet_template="").get(device_type=device_type)
    except LendingProfile.DoesNotExist:
        raise Http404(f"No lending slip template configured for device type '{device_type}'.")

    return TemplateResponse(
        request,
        f"lending/db/{profile.pk}.html",
        {"record": unsaved_record, "lending_profile": profile},
    )


@login_required
@permission_required("core.view_lentrecord", raise_exception=True)
def print_lent_sheet(request, pk):
    """
    Render the lending slip for an already *saved* lent record. Reached from
    the LentRecord admin change form (moved unchanged from dlcdb.core, now
    with a permission gate); ``print_sheet`` above is the unsaved-form variant.
    """
    record = get_object_or_404(LentRecord, pk=pk)

    device_type = record.device.device_type
    if not device_type:
        raise Http404("Device has no device type assigned.")

    try:
        profile = LendingProfile.objects.exclude(lent_sheet_template="").get(device_type=device_type)
    except LendingProfile.DoesNotExist:
        raise Http404(f"No lending slip template configured for device type '{device_type}'.")

    template_name = f"lending/db/{profile.pk}.html"
    context = {
        "record": record,
        "lending_profile": profile,
    }
    return TemplateResponse(request, template_name, context)
