# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Frontends for the simple device master data: device types, manufacturers and
suppliers. Three near-identical list/add/edit surfaces sharing one
implementation, parameterized by a small spec per model.
"""

from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.forms import ModelForm
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from dlcdb.core.models import DeviceType, Manufacturer, Supplier
from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.pagination import paginate

from ..filters import DeviceTypeFilter, ManufacturerFilter, SupplierFilter
from ..forms import DeviceTypeForm, ManufacturerForm, SupplierForm

MASTERDATA_PER_PAGE = 25


@dataclass(frozen=True)
class MasterdataSpec:
    """Everything that differs between the three master-data surfaces."""

    model: type
    form_class: type[ModelForm]
    filter_class: type
    index_template: str
    list_id: str
    index_url: str
    detail_url: str
    change_permission: str
    heading: str
    icon: str
    add_title: str
    submit_label: str
    search_placeholder: str
    # DeviceFilter param that filters the device index by this model, so the
    # detail page's device count can link to the actual devices.
    device_filter_param: str
    # DeviceType is an audit model (user/username/timestamps); Manufacturer and
    # Supplier are plain models without those fields.
    has_audit_fields: bool


DEVICE_TYPE_SPEC = MasterdataSpec(
    model=DeviceType,
    form_class=DeviceTypeForm,
    filter_class=DeviceTypeFilter,
    index_template="assets/device_types/index.html",
    list_id="device-type-list",
    index_url="assets:device_type_index",
    detail_url="assets:device_type_detail",
    change_permission="core.change_devicetype",
    heading=gettext_lazy("Device type"),
    icon="bi-palette",
    add_title=gettext_lazy("Add device type"),
    submit_label=gettext_lazy("Create device type"),
    search_placeholder=gettext_lazy("Search name, prefix..."),
    device_filter_param="device_type",
    has_audit_fields=True,
)

MANUFACTURER_SPEC = MasterdataSpec(
    model=Manufacturer,
    form_class=ManufacturerForm,
    filter_class=ManufacturerFilter,
    index_template="assets/manufacturers/index.html",
    list_id="manufacturer-list",
    index_url="assets:manufacturer_index",
    detail_url="assets:manufacturer_detail",
    change_permission="core.change_manufacturer",
    heading=gettext_lazy("Manufacturer"),
    icon="bi-building",
    add_title=gettext_lazy("Add manufacturer"),
    submit_label=gettext_lazy("Create manufacturer"),
    search_placeholder=gettext_lazy("Search name, note..."),
    device_filter_param="manufacturer",
    has_audit_fields=False,
)

SUPPLIER_SPEC = MasterdataSpec(
    model=Supplier,
    form_class=SupplierForm,
    filter_class=SupplierFilter,
    index_template="assets/suppliers/index.html",
    list_id="supplier-list",
    index_url="assets:supplier_index",
    detail_url="assets:supplier_detail",
    change_permission="core.change_supplier",
    heading=gettext_lazy("Supplier"),
    icon="bi-truck",
    add_title=gettext_lazy("Add supplier"),
    submit_label=gettext_lazy("Create supplier"),
    search_placeholder=gettext_lazy("Search name, note..."),
    device_filter_param="supplier",
    has_audit_fields=False,
)


def _masterdata_queryset(spec):
    """
    All objects (the soft-delete default managers already exclude deleted
    rows), each annotated with the count of devices referencing it — the same
    count the admin's DeviceCountMixin shows.
    """
    return spec.model.objects.annotate(assets_count=Count("device", distinct=True))


def _masterdata_index(request, spec):
    template = f"{spec.index_template}#{spec.list_id}" if request.htmx else spec.index_template
    base_queryset = _masterdata_queryset(spec)

    data = request.GET.copy()
    data.setdefault("ordering", "name")
    filterset = spec.filter_class(data, queryset=base_queryset, request=request)

    page_obj = paginate(request, filterset.qs, MASTERDATA_PER_PAGE)

    context = {
        "filter": filterset,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            filterset,
            request,
            target=f"#{spec.list_id}",
            search_placeholder=spec.search_placeholder,
        ),
        "current_ordering": data["ordering"],
        "filtered_count": page_obj.paginator.count,
        "total_count": base_queryset.count(),
    }
    return TemplateResponse(request, template, context)


def _masterdata_add(request, spec):
    form = spec.form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if spec.has_audit_fields:
            obj.user, obj.username = get_denormalized_user(request.user)
        obj.save()
        messages.success(
            request,
            _("%(model)s “%(obj)s” was created.") % {"model": spec.model._meta.verbose_name, "obj": obj},
        )
        return redirect(spec.detail_url, pk=obj.pk)

    return TemplateResponse(
        request,
        "assets/masterdata/form.html",
        {
            "form": form,
            "title": spec.add_title,
            "submit_label": spec.submit_label,
            "heading": spec.heading,
            "icon": spec.icon,
            "index_url": reverse(spec.index_url),
        },
    )


def _masterdata_detail(request, spec, pk):
    obj = get_object_or_404(_masterdata_queryset(spec), pk=pk)
    can_change = request.user.has_perm(spec.change_permission)

    # The index threads its active search/filter/sort here as ?next= so Save,
    # Back and Cancel return to the exact filtered list.
    next_query = request.GET.get("next", "")
    index_url = reverse(spec.index_url)
    if next_query:
        index_url = f"{index_url}?{next_query}"
    form_action = reverse(spec.detail_url, args=[obj.pk])
    if next_query:
        form_action += "?" + urlencode({"next": next_query})

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied
        form = spec.form_class(request.POST, instance=obj)
        if form.is_valid():
            saved_obj = form.save(commit=False)
            if spec.has_audit_fields:
                saved_obj.user, saved_obj.username = get_denormalized_user(request.user)
            saved_obj.save()
            messages.success(
                request,
                _("%(model)s “%(obj)s” was updated.") % {"model": spec.model._meta.verbose_name, "obj": saved_obj},
            )
            return redirect(index_url)
    else:
        form = spec.form_class(instance=obj)

    return TemplateResponse(
        request,
        "assets/masterdata/detail.html",
        {
            "object": obj,
            "form": form,
            "can_change": can_change,
            "heading": spec.heading,
            "icon": spec.icon,
            "has_audit_fields": spec.has_audit_fields,
            "index_url": index_url,
            "form_action": form_action,
            "devices_url": f"{reverse('assets:device_index')}?{spec.device_filter_param}={obj.pk}",
        },
    )


@permission_required("core.view_devicetype", raise_exception=True)
def device_type_index(request):
    return _masterdata_index(request, DEVICE_TYPE_SPEC)


@permission_required("core.add_devicetype", raise_exception=True)
def device_type_add(request):
    return _masterdata_add(request, DEVICE_TYPE_SPEC)


@permission_required("core.view_devicetype", raise_exception=True)
def device_type_detail(request, pk):
    return _masterdata_detail(request, DEVICE_TYPE_SPEC, pk)


@permission_required("core.view_manufacturer", raise_exception=True)
def manufacturer_index(request):
    return _masterdata_index(request, MANUFACTURER_SPEC)


@permission_required("core.add_manufacturer", raise_exception=True)
def manufacturer_add(request):
    return _masterdata_add(request, MANUFACTURER_SPEC)


@permission_required("core.view_manufacturer", raise_exception=True)
def manufacturer_detail(request, pk):
    return _masterdata_detail(request, MANUFACTURER_SPEC, pk)


@permission_required("core.view_supplier", raise_exception=True)
def supplier_index(request):
    return _masterdata_index(request, SUPPLIER_SPEC)


@permission_required("core.add_supplier", raise_exception=True)
def supplier_add(request):
    return _masterdata_add(request, SUPPLIER_SPEC)


@permission_required("core.view_supplier", raise_exception=True)
def supplier_detail(request, pk):
    return _masterdata_detail(request, SUPPLIER_SPEC, pk)
