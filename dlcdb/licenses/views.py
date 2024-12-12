from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.utils.translation import gettext as _

from django_htmx.http import HttpResponseClientRedirect

from dlcdb.core.models import LicenceRecord, Device, InRoomRecord, Room
from .forms import LicenseForm
from .decorators import htmx_permission_required
from .filters import LicenceRecordFilter


@login_required
def index(request):
    if request.htmx:
        template = "licenses/licenses_table.html"
    else:
        template = "licenses/index.html"

    base_qs = LicenceRecord.objects.all().order_by("-device__modified_at")
    license_record_filter = LicenceRecordFilter(request.GET, queryset=base_qs)

    context = {
        "licenses_filtered": license_record_filter.qs.count(),
        "licenses_total": base_qs.count(),
        "license_record_filter": license_record_filter,
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

    license = get_object_or_404(Device, id=license_id)

    if request.method == "POST":
        form = LicenseForm(
            request.POST,
            instance=license,
        )

        if form.is_valid():
            device = form.save(commit=True)
            device.save()

            messages.success(
                request,
                f"License {device.sap_id} saved.",
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
        form = LicenseForm(
            instance=license,
        )

    return TemplateResponse(
        request,
        template,
        {
            "form": form,
            "license": license,
            "template": template,
            "title": _("Edit license"),
            "obj_admin_url": reverse("admin:core_device_change", args=[license.id]),
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
            "title": _("New license"),
        },
    )
