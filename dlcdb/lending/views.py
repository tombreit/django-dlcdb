# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BooleanField, Case, CharField, Count, Exists, IntegerField, OuterRef, Q, Value, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core.models import InRoomRecord, LentRecord, Person, Record, Room
from dlcdb.core.models.record import RECORD_TYPE_COLORS
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.core.utils.tenants import tenant_scoped_queryset

from .decorators import htmx_permission_required
from .filters import (
    LendingDeviceFilter,
    LendingPersonFilter,
    LentRecordFilter,
    STATE_OVERDUE,
    STATE_LENT,
    STATE_AVAILABLE,
)
from .forms import LentingForm
from .models import LendingConfiguration, LendingProfile


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
    # Derive badge colours from the single record_type→colour map so the lending
    # list and the asset card cannot disagree (see core.models.record).
    color_whens += [
        When(record_type=Record.LENT, then=Value(RECORD_TYPE_COLORS[Record.LENT])),
        When(record_type=Record.INROOM, then=Value(RECORD_TYPE_COLORS[Record.INROOM])),
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


@login_required
def index(request):
    """
    Overview of lendable devices: what is currently lent to whom and what is
    available, with live HTMX search/filtering and bookmarkable URLs.
    """
    template = "lending/index.html#lent-list" if request.htmx else "lending/index.html"

    base_qs = _annotate_lent_state(
        _tenant_scoped(
            LentRecord.objects.select_related("device__manufacturer", "person", "room"),
            request,
        )
    )

    lent_record_filter = LentRecordFilter(request.GET, queryset=base_qs, request=request)

    counts = lent_record_filter.qs.aggregate(
        total=Count("pk"),
        available=Count("pk", filter=Q(record_type=Record.INROOM)),
        lent=Count("pk", filter=Q(record_type=Record.LENT)),
    )

    context = {
        "filter": lent_record_filter,
        "lent_filtered_count": counts["total"],
        "lent_total_count": base_qs.count(),
        "lent_available_count": counts["available"],
        "lent_lent_count": counts["lent"],
    }

    return TemplateResponse(request, template, context)


def _get_scoped_record(request, pk):
    """
    Fetch the lending record for ``pk``, scoped to the request's tenant so a
    user can only open rows they can also see on the index. Returns a 404 for
    out-of-tenant or non-lentable (e.g. REMOVED) records.
    """
    return get_object_or_404(
        _tenant_scoped(LentRecord.objects.select_related("device", "person", "room"), request),
        pk=pk,
    )


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
        messages.warning(request, _("Warning: No UDB contract end date found for %(person)s!") % {"person": person})
    elif desired_end and desired_end >= contract_end:
        messages.warning(request, _("Warning: Contract ends before the desired return date!"))


def _apply_state_machine(record, form, user, username):
    """
    Replicates the state machine of ``LentRecordAdmin.save_model``:

    - INROOM (available) -> create a new LENT record (lend the device).
    - LENT + return date -> save the LENT record, then create an auto-return
      InRoomRecord (device becomes available again).
    - LENT, no return date -> just save the edited LENT record.
    """
    obj = form.save(commit=False)

    if record.record_type == Record.LENT and obj.lent_end_date:
        obj.user, obj.username = user, username
        obj.save()
        InRoomRecord(
            device=obj.device,
            room=Room.objects.get(is_auto_return_room=True),
            user=user,
            username=username,
        ).save()

    elif record.record_type == Record.LENT:
        obj.user, obj.username = user, username
        obj.save()

    elif record.record_type == Record.INROOM:
        # Build a fresh LentRecord instead of saving the INROOM proxy, whose
        # save() would force-flip the existing INROOM record to LENT.
        LentRecord(
            device=record.device,
            room=form.cleaned_data["room"],
            person=form.cleaned_data["person"],
            lent_start_date=form.cleaned_data["lent_start_date"],
            lent_desired_end_date=form.cleaned_data["lent_desired_end_date"],
            lent_note=form.cleaned_data.get("lent_note", ""),
            lent_reason=form.cleaned_data.get("lent_reason", ""),
            lent_accessories=form.cleaned_data.get("lent_accessories", ""),
            user=user,
            username=username,
        ).save()

    else:
        raise ValidationError(_("Lent state unknown - please report this issue!"))


def _save_lending(request, record, form):
    """
    Run the soft warnings and the lend/return/edit state machine in one
    transaction. Returns True on success (caller should redirect) or False if a
    form error was added (caller should re-render). Shared by ``detail`` and
    ``quick_lend``.
    """
    user, username = get_denormalized_user(request.user)
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
        msg = _("Device “%(device)s” lent to “%(person)s”.")
    elif record.lent_end_date or form.cleaned_data.get("lent_end_date"):
        msg = _("Return of “%(device)s” from “%(person)s” acknowledged.")
    else:
        msg = _("Lending of “%(device)s” to “%(person)s” saved.")
    messages.success(request, msg % {"device": record.device, "person": form.cleaned_data.get("person")})
    return True


@login_required
@htmx_permission_required("core.change_lentrecord")
def detail(request, pk):
    """
    Lend an available device to a person, or acknowledge the return of / edit a
    currently lent device. Replaces the django-admin LentRecord change view.
    """
    record = _get_scoped_record(request, pk)
    device = record.device

    if record.record_type == Record.LOST:
        messages.error(request, _('Device is currently "not locatable" and must be located first.'))
        return redirect("lending:index")

    if request.method == "POST":
        form = LentingForm(request.POST, instance=record, record_type=record.record_type)
        if form.is_valid() and _save_lending(request, record, form):
            return redirect("lending:index")
    else:
        form = LentingForm(instance=record, record_type=record.record_type)

    # Keep the visually selected person card in sync after a failed POST, where
    # the picked person lives only in the submitted (hidden) person field.
    selected_person = record.person
    if request.method == "POST":
        submitted_person_id = request.POST.get("person")
        if submitted_person_id:
            selected_person = Person.objects.filter(pk=submitted_person_id).first() or record.person

    context = {
        "form": form,
        "record": record,
        "device": device,
        "selected_person": selected_person,
        "is_lend_flow": record.record_type == Record.INROOM,
        "is_return_flow": record.record_type == Record.LENT,
        "title": _("Lend device") if record.record_type == Record.INROOM else _("Lending"),
        "obj_admin_url": reverse("admin:core_lentrecord_change", args=[record.pk]),
        "has_lending_profile": LendingProfile.objects.filter(device_type=device.device_type).exists(),
    }
    return TemplateResponse(request, "lending/detail.html", context)


@login_required
@htmx_permission_required("core.change_lentrecord")
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


def _available_devices(request):
    """Tenant-scoped queryset of available (INROOM), lentable devices to lend.

    Annotates ``has_lending_profile`` so the device picker can tell whether an
    Ausleihzettel (lending slip) can be printed for the device.
    """
    return _tenant_scoped(
        LentRecord.objects.filter(record_type=Record.INROOM)
        .select_related("device__manufacturer", "room")
        .annotate(
            has_lending_profile=Exists(LendingProfile.objects.filter(device_type=OuterRef("device__device_type")))
        ),
        request,
    )


@login_required
@htmx_permission_required("core.change_lentrecord")
def device_search(request):
    """HTMX live-search backing the device picker in the quick-lend assistant."""
    device_filter = LendingDeviceFilter(request.POST or None, queryset=_available_devices(request))
    return TemplateResponse(
        request,
        "lending/includes/_device_search_results.html",
        {"filter": device_filter},
    )


@login_required
@htmx_permission_required("core.change_lentrecord")
def quick_lend(request):
    """
    One-screen "shortcut lending" assistant: pick an available device and a
    person (either order), a room, and create the lending in a single submit.
    Reuses the same lend path as the detail view via ``_save_lending``.
    """
    selected_device = None
    selected_person = None

    if request.method == "POST":
        record_pk = request.POST.get("device_record")
        if not record_pk:
            messages.error(request, _("Please select a device to lend."))
            return redirect("lending:quick_lend")

        record = _get_scoped_record(request, record_pk)
        if record.record_type != Record.INROOM:
            messages.error(request, _("This device is no longer available for lending."))
            return redirect("lending:quick_lend")

        form = LentingForm(request.POST, instance=record, record_type=record.record_type)
        if form.is_valid() and _save_lending(request, record, form):
            return redirect("lending:index")

        # Validation failed: keep the picked device/person cards on re-render
        # (they otherwise live only in the hidden fields).
        selected_device = record
        person_id = request.POST.get("person")
        if person_id:
            selected_person = Person.objects.filter(pk=person_id).first()
    else:
        form = LentingForm(record_type=Record.INROOM)

    context = {
        "form": form,
        "title": _("Quick lend"),
        "selected_device": selected_device,
        "selected_person": selected_person,
    }
    return TemplateResponse(request, "lending/quick_lend.html", context)


def _build_unsaved_lentrecord(device, form):
    """Construct an unsaved LentRecord from (possibly partial) form data."""
    person_id = form.data.get("person")
    person = Person.objects.filter(pk=person_id).first() if person_id else None
    return LentRecord(
        device=device,
        person=person,
        room=form.cleaned_data.get("room"),
        lent_start_date=form.cleaned_data.get("lent_start_date"),
        lent_desired_end_date=form.cleaned_data.get("lent_desired_end_date"),
        lent_accessories=form.data.get("lent_accessories", ""),
        lent_note=form.data.get("lent_note", ""),
        lent_reason=form.data.get("lent_reason", ""),
    )


@login_required
@htmx_permission_required("core.change_lentrecord")
@require_POST
def print_sheet(request, pk):
    """
    Render the "Ausleihzettel" (lending slip) from the *unsaved* form data, so
    helpdesk can print and have it signed before committing the lending.
    Generalizes ``core.views.lent_management_views.print_lent_sheet``.
    """
    record = _get_scoped_record(request, pk)
    device = record.device

    form = LentingForm(request.POST, instance=record, record_type=record.record_type)
    # Populate cleaned_data without hard-blocking on validation: a slip should
    # print even from a partially filled form.
    form.is_valid()

    unsaved_record = _build_unsaved_lentrecord(device, form)

    device_type = device.device_type
    if not device_type:
        raise Http404("Device has no device type assigned.")

    try:
        profile = LendingProfile.objects.get(device_type=device_type)
    except LendingProfile.DoesNotExist:
        raise Http404(f"No lending profile configured for device type '{device_type}'.")

    return TemplateResponse(
        request,
        f"lending/db/{profile.pk}.html",
        {"record": unsaved_record, "lending_profile": profile},
    )
