from datetime import datetime, timedelta

from django.template.response import TemplateResponse
from django.db.models import Q, Case, CharField, Value, When
from django.shortcuts import redirect, get_object_or_404
from django.http.response import HttpResponseRedirectBase
from django.contrib.auth.decorators import login_required

from dlcdb.core.models import LicenceRecord, Device
from dlcdb.reporting.models import Notification
from .forms import LicenseForm
from .subscribers import manage_subscribers


class HttpResponseSeeOther(HttpResponseRedirectBase):
    status_code = 303


@login_required
def index(request):
    q = request.GET.get("q")

    if request.htmx:
        template = "licenses/licenses_table.html"
    else:
        template = "licenses/index.html"

    now = datetime.today().date()
    threshold = now + timedelta(days=60)  # now plus two months

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

    if q:
        search_filter = (
            Q(device__manufacturer__name__icontains=q) | Q(device__series__icontains=q) | Q(device__sap_id__icontains=q)
        )
        qs = base_qs.filter(search_filter)
    else:
        qs = base_qs

    context = {
        "licenses": qs,
        "licences_total": base_qs.count(),
    }

    return TemplateResponse(request, template, context)


@login_required
def new(request):
    # TODO: Implement this view
    return TemplateResponse(request, "", {})


@login_required
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
            initial={
                "user": request.user,
            },
        )

        if form.is_valid():
            device = form.save(commit=False)
            device.user = request.user

            subscribers = form.cleaned_data["subscribers"]
            manage_subscribers(device, subscribers)

            device.save()

            # messages.success(
            #     request,
            #     f"License {device.sap_id} saved.",
            # )

            return redirect("licenses:index")

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
        },
    )
