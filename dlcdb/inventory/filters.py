# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import django_filters
from django.db.models import Q

from ..core.models import Room, Device, DeviceType, Record, Inventory
from .forms import DeviceSearchForm


class RoomFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="string_search_filter", label="Search rooms")

    def string_search_filter(self, queryset, name, value):
        return Inventory.objects.tenant_aware_room_objects(self.request.tenant).filter(
            Q(number__icontains=value) | Q(nickname__icontains=value) | Q(description__icontains=value)
        )

    class Meta:
        model = Room
        # form = RoomSearchForm
        fields = ["q"]


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
