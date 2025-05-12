from functools import reduce
from operator import or_

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import LicenceRecord, DeviceType, Supplier


class LicenceRecordFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter_method")

    def search_filter_method(self, queryset, name, value):
        return queryset.filter(
            Q(device__manufacturer__name__icontains=value)
            | Q(device__series__icontains=value)
            | Q(device__sap_id__icontains=value)
            | Q(device__supplier__name__icontains=value)
            | Q(device_human_title__icontains=value)
        )

    _license_type_prefixes = ["Lizenz::", "License::", "Licence::"]
    _license_type_queries = [Q(name__startswith=prefix) for prefix in _license_type_prefixes]
    device__device_type = django_filters.ModelChoiceFilter(
        queryset=DeviceType.objects.filter(reduce(or_, _license_type_queries)),
        empty_label=_("License type..."),
    )

    device__supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.filter(device__is_licence=True, device__isnull=False).distinct(),
        empty_label=_("Supplier..."),
    )

    def get_license_state_choices():
        choices = [
            (state, LicenceRecord.get_localized_license_state_label(for_state=state))
            for state in LicenceRecord.objects.values_list("license_state", flat=True)
            .exclude(license_state__isnull=True)
            .exclude(license_state__exact="")
            .distinct()
            .order_by("license_state")
        ]
        return choices

    license_state = django_filters.ChoiceFilter(
        choices=get_license_state_choices,
        empty_label=_("License state..."),
    )

    class Meta:
        model = LicenceRecord
        fields = ["search", "device__device_type", "device__supplier", "license_state"]
