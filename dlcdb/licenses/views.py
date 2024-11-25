from datetime import datetime, timedelta

from django.template.response import TemplateResponse
from django.db.models import Q, Case, CharField, Value, When
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse

from django_htmx.http import HttpResponseClientRedirect

from dlcdb.core.models import LicenceRecord, Device, InRoomRecord, Room, DeviceType
from dlcdb.reporting.models import Notification
from .forms import LicenseForm
from .subscribers import manage_subscribers
from .decorators import htmx_permission_required


@login_required
def index(request):
    q = request.GET.get("q")
    license_type = request.GET.get("license-type-select")

    if request.htmx:
        template = "licenses/licenses_table.html"
    else:
        template = "licenses/index.html"

    now = datetime.today().date()
    threshold = now + timedelta(days=30)  # now plus one months

    base_qs = (
        LicenceRecord.objects.select_related("device", "device__manufacturer", "device__device_type")
        .prefetch_related("device__notification_set")
        .annotate(
            licence_state=Case(
                When(
                    device__maintenance_contract_expiration_date__lte=now,
                    then=Value("90-danger"),
                ),
                When(
                    device__maintenance_contract_expiration_date__gt=now,
                    device__maintenance_contract_expiration_date__lte=threshold,
                    then=Value("80-warning"),
                ),
                default=Value("10-unknown"),
                output_field=CharField(),
            )
        )
        .order_by("-licence_state", "device__maintenance_contract_expiration_date")
    )

    # Limit device-type choices to "License-type" choices
    license_type_choices = DeviceType.objects.filter(
        Q(name__startswith="Lizenz::") | Q(name__startswith="License::") | Q(name__startswith="Licence::")
    )

    # Filtering the queryset
    if q:
        search_filter = (
            Q(device__manufacturer__name__icontains=q) | Q(device__series__icontains=q) | Q(device__sap_id__icontains=q)
        )
        qs = base_qs.filter(search_filter)
    else:
        qs = base_qs

    if license_type and license_type != "0":
        qs = qs.filter(device__device_type=license_type)

    context = {
        "licenses": qs,
        "licenses_filtered": qs.count(),
        "licenses_total": base_qs.count(),
        "license_type_choices": license_type_choices,
    }

    return TemplateResponse(request, template, context)


@login_required
@htmx_permission_required("core.change_licencerecord")
def edit(request, license_id):
    if request.htmx:
        template = "licenses/form.html"
    else:
        raise NotImplementedError("Non HTMX requests not implemented")

    license = get_object_or_404(Device, id=license_id)

    if request.method == "POST":
        form = LicenseForm(
            request.POST,
            instance=license,
        )

        if form.is_valid():
            device = form.save(commit=False)
            device.save()

            subscribers = form.cleaned_data["subscribers"]
            manage_subscribers(device, subscribers)

            messages.success(
                request,
                f"License {device.sap_id} saved.",
            )

            # The plain return redirect() behaves differently than the HX-Redirect header
            # return redirect("licenses:index")
            # This redirect is also available in the Django HTMX package:
            # return HttpResponseClientRedirect(redirect_url)
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("licenses:index")
            return response

    else:
        subscribers = Notification.objects.filter(device=license).values_list("recipient", flat=True)

        form = LicenseForm(
            instance=license,
            initial={
                "subscribers": ", ".join(subscribers),
            },
        )

    return TemplateResponse(
        request,
        template,
        {
            "form": form,
            "license": license,
            "template": template,
            "title": "Edit license",
            "obj_admin_url": reverse("admin:core_device_change", args=[license.id]),
        },
    )


@login_required
@htmx_permission_required("core.change_licencerecord")
def new(request):
    if request.htmx:
        template = "licenses/form.html"
    else:
        raise NotImplementedError("Non HTMX requests not implemented")

    if request.method == "POST":
        form = LicenseForm(
            request.POST,
        )

        # TODO: As we have only optional fields, check if at least one field is filled
        if form.is_valid():
            # The form.is_valid() call will trigger the custom validation
            # defined in your LicenseForm class's clean() method
            device = form.save(commit=False)

            # Set device properties
            device.is_licence = True
            device.save()

            # Set record for device
            try:
                room = Room.objects.get(is_default_license_room=True)
            except Room.DoesNotExist:
                # TODO: Emit a human readable error message instead of a 500
                raise ValidationError("No license room/location defined. Define a license room first.")

            record = InRoomRecord(
                device=device,
                room=room,
                user=request.user,
                username=request.user.username,
            )
            record.save()

            subscribers = form.cleaned_data["subscribers"]
            manage_subscribers(device, subscribers)

            messages.success(
                request,
                f"License {device.sap_id} added.",
            )

            redirect_url = reverse("licenses:index")
            return HttpResponseClientRedirect(redirect_url)
    else:
        form = LicenseForm()

    return TemplateResponse(
        request,
        template,
        {
            "form": form,
            "template": template,
            "title": "New license",
        },
    )
