# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..core.models import Device, DeviceType, Inventory, Record, Room
from ..core.models.inventory import get_active_inventory
from ..tenants.models import Tenant
from .forms import DeviceSearchForm


class RoomFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="string_search_filter", label="Search rooms")

    def string_search_filter(self, queryset, name, value):
        return Inventory.objects.tenant_aware_room_objects(tenants=self.request.tenants).filter(
            Q(number__icontains=value) | Q(nickname__icontains=value) | Q(description__icontains=value)
        )

    class Meta:
        model = Room
        # form = RoomSearchForm
        fields = ["q"]


def search_tenants(request):
    """
    Tenant choices of the device search: the user's own tenants, unless the
    active inventory searches across all tenants (``device_search_tenant_aware``
    switched off).
    """
    if request is None:
        return Tenant.objects.none()
    inventory = get_active_inventory(request)
    if inventory and not inventory.device_search_tenant_aware:
        return Tenant.objects.all()
    return Tenant.objects.filter(pk__in=[tenant.pk for tenant in request.tenants])


class DeviceFilter(django_filters.FilterSet):
    OUTSTANDING_CHOICES = (
        ("outstanding", "Outstanding"),
        ("done", "Done"),
    )

    def filter_not_already_inventorized(self, queryset, name, value):
        if value == "outstanding":
            return (
                queryset.exclude(sap_id__isnull=True)
                .exclude(sap_id__exact="")
                .exclude(record__inventory=Inventory.objects.active_inventory())
                .distinct()
            )
        elif value == "done":
            return (
                queryset.exclude(sap_id__isnull=True)
                .exclude(sap_id__exact="")
                .filter(record__inventory=Inventory.objects.active_inventory())
                .distinct()
            )

    q = django_filters.CharFilter(method="string_search_filter", label="Search devices")
    device_type = django_filters.ModelChoiceFilter(queryset=DeviceType.objects.all(), label="Geräteklasse")
    record = django_filters.ChoiceFilter(
        field_name="active_record__record_type", choices=Record.RECORD_TYPE_CHOICES, label="Record"
    )
    not_already_inventorized = django_filters.ChoiceFilter(
        field_name="not_already_inventorized",
        method="filter_not_already_inventorized",
        label="Outstanding",
        choices=OUTSTANDING_CHOICES,
    )
    tenant = django_filters.ModelChoiceFilter(queryset=search_tenants, label=_("Tenant"))

    def string_search_filter(self, queryset, name, value):
        return self.queryset.filter(
            Q(edv_id__icontains=value)
            | Q(sap_id__icontains=value)
            | Q(series__icontains=value)
            | Q(manufacturer__name__icontains=value)
        )

    class Meta:
        model = Device
        form = DeviceSearchForm
        fields = [
            "not_already_inventorized",
            "id",
            "tenant",
        ]
