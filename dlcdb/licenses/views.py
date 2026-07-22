# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import traceback

from itertools import chain
from operator import attrgetter

from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.db.models import OuterRef, Subquery

from django_htmx.http import HttpResponseClientRedirect

from dlcdb.core import lifecycle
from dlcdb.core.models import LicenceRecord, Room, Device
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.pagination import paginate
from .forms import LicenseForm
from .decorators import htmx_permission_required
from .filters import LicenceRecordFilter
from .models import LicensesConfiguration, LicenseAsset

# Rows per page for the licenses list. Mirrors dlcdb.assets.views.devices.
LICENSES_PER_PAGE = 25


@login_required
def _playground(request):
    """
    Just a temporary playground view.
    """
    template = "licenses/playground.html"
    context = {}

    return TemplateResponse(request, template, context)


@login_required
def index(request):
    template = "licenses/index.html#licenses-list" if request.htmx else "licenses/index.html"

    base_qs = LicenceRecord.objects.annotate(
        device_human_title=Subquery(LicenseAsset.objects.filter(pk=OuterRef("device_id")).values("human_title")[:1])
    )

    # Always supply a default ordering so a bare page load is deterministic;
    # an explicit header/dropdown click still wins. Mirrors device_index.
    data = request.GET.copy()
    data.setdefault("ordering", "-modified")
    license_record_filter = LicenceRecordFilter(data, queryset=base_qs, request=request)

    page_obj = paginate(request, license_record_filter.qs, LICENSES_PER_PAGE)

    context = {
        "license_record_filter": license_record_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            license_record_filter,
            request,
            target="#licenses-list",
            search_placeholder=_("Search title, manufacturer, supplier, inventory ID..."),
        ),
        "current_ordering": data["ordering"],
        # paginator.count runs the filtered COUNT once; reuse it here.
        "licenses_filtered": page_obj.paginator.count,
        "licenses_total": base_qs.count(),
    }

    return TemplateResponse(request, template, context)


@login_required
@htmx_permission_required("core.change_licencerecord")
def edit(request, license_id):
    if request.htmx:
        template = "licenses/form_partial.html"
    else:
        # raise NotImplementedError("Non HTMX requests not implemented")
        template = "licenses/form.html"

    # Fetch the concrete Device model directly, as django-simple-history
    # does not support proxy models for the history.
    device = get_object_or_404(Device, id=license_id)

    if request.method == "POST":
        form = LicenseForm(
            request.POST,
            instance=device,
        )

        if form.is_valid():
            device = form.save(commit=False)
            device.save()

            messages.success(
                request,
                f"License {device.human_title} saved.",
            )

            # The plain return redirect() behaves differently than the HX-Redirect header
            # return redirect("licenses:index")
            # This redirect is also available in the Django HTMX package:
            # return HttpResponseClientRedirect(redirect_url)
            if request.htmx:
                response = HttpResponse(status=204)
                response["HX-Redirect"] = reverse("licenses:index")
                return response
            else:
                return redirect("licenses:index")

    else:
        # GET request
        form = LicenseForm(
            instance=device,
        )

    # Determine if calendar URL should be shown (check for relevant dates)
    calendar_url = False
    if device.contract_start_date or device.contract_expiration_date:
        calendar_url = reverse("licenses:license_calendar", args=[device.uuid])

    return TemplateResponse(
        request,
        template,
        {
            "form": form,
            "license": device,
            "template": template,
            "title": _("Edit license"),
            "obj_admin_url": reverse("admin:core_device_change", args=[device.id]),
            "calendar_url": calendar_url,
        },
    )


@login_required
@htmx_permission_required("core.change_licencerecord")
def new(request):
    if request.htmx:
        template = "licenses/form_partial.html"
    else:
        raise NotImplementedError("Non HTMX requests not implemented")

    if request.method == "POST":
        form = LicenseForm(
            request.POST,
        )

        if form.is_valid():
            errors = []

            try:
                with transaction.atomic():
                    # The form.is_valid() call will trigger the custom validation
                    # defined in your LicenseForm class's clean() method
                    device = form.save(commit=False)

                    # Set device properties
                    device.is_licence = True
                    device.save()

                    # Set record and room for device -- a new licence's first
                    # record locates it in the default licence room.
                    room = Room.objects.get(is_default_license_room=True)
                    lifecycle.transition_locate(device, room=room, user=request.user)

            except Room.DoesNotExist:
                errors.append("No license room/location defined. Define a license room first.")
            except ValidationError as e:
                errors.append(str(e))
            except IntegrityError as e:
                errors.append(f"Database error: Could not save the license. Please try again. Error: {e}")
            except Exception as e:
                stacktrace = traceback.format_exc()
                errors.append(f"An error occurred while saving: {e}\n{stacktrace}")

            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.success(
                    request,
                    f"License {device.sap_id} added.",
                )

            redirect_url = reverse("licenses:index")
            return HttpResponseClientRedirect(redirect_url)
    else:
        # Set default subscribers
        default_subscribers = LicensesConfiguration.load().default_subscribers.all()
        form = LicenseForm(initial={"subscribers": default_subscribers})

    return TemplateResponse(
        request,
        template,
        {
            "form": form,
            "template": template,
            "title": _("New license"),
        },
    )


@login_required
@htmx_permission_required("core.change_licencerecord")
def history(request, license_id):
    device = get_object_or_404(LicenseAsset, id=license_id)
    device_history = device.history.all()

    # subscription_model = device.subscription_set.model
    # deleted_subscription_history = subscription_model.history.filter(device_id=device.id)
    # Currently we do not need the combined history of multiple models
    # as the subscribers changes are tracked manually with the
    # update_change_reason function.
    combined_history = sorted(chain(device_history), key=attrgetter("history_date"), reverse=True)

    # Use a generator function to yield history entries with diffs
    def get_history_with_diffs():
        history_list = list(combined_history)
        for i in range(len(history_list) - 1):
            record = history_list[i]
            next_record = history_list[i + 1]

            # Check if both records are from the same model
            if isinstance(record.instance, type(next_record.instance)):
                # They are the same model; compute the diff
                delta = record.diff_against(
                    next_record, foreign_keys_are_objs=True, excluded_fields=["id", "active_record", "subscriber"]
                )
                # Skip if no changes detected
                if not delta.changes and not record.history_change_reason:
                    continue
            else:
                # Different models; cannot compute diff
                # delta = None
                if not record.history_change_reason:
                    continue

            yield (record, delta)

        # Handle the last record
        if history_list and history_list[-1].history_change_reason:
            yield (history_list[-1], None)
        # Handle the last record
        if history_list:
            yield (history_list[-1], None)

    return TemplateResponse(
        request,
        "licenses/history.html",
        {
            "history": get_history_with_diffs(),
            "license": device,
            "title": _("License History"),
        },
    )
