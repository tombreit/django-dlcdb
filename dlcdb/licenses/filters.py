from functools import reduce
from operator import or_

import django_filters
from django.db.models import Q

from dlcdb.core.models import LicenceRecord, DeviceType, Supplier


class LicenceRecordFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter_method")

    def search_filter_method(self, queryset, name, value):
        return queryset.filter(
            Q(device__manufacturer__name__icontains=value)
            | Q(device__series__icontains=value)
            | Q(device__sap_id__icontains=value)
        )

    prefixes = ["Lizenz::", "License::", "Licence::"]
    queries = [Q(name__startswith=prefix) for prefix in prefixes]
    device__device_type = django_filters.ModelChoiceFilter(queryset=DeviceType.objects.filter(reduce(or_, queries)))

    device__supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.filter(device__is_licence=True, device__isnull=False).distinct()
    )

    # license_state = django_filters.CharFilter(field_name="license_state")
    license_state = django_filters.ChoiceFilter(
        choices=(
            lambda: [
                (state, LicenceRecord.get_localized_license_state_label(for_state=state))
                for state in LicenceRecord.objects.values_list("license_state", flat=True)
                .exclude(license_state__isnull=True)
                .exclude(license_state__exact="")
                .distinct()
                .order_by("license_state")
            ]
        )()
    )

    class Meta:
        model = LicenceRecord
        fields = ["search", "device__device_type", "device__supplier", "license_state"]
        # filter_overrides = {
        #     "device__supplier": {
        #         "filter_class": django_filters.ModelChoiceFilter,
        #         "extra": lambda f: {
        #             "queryset": f.related_model.objects.filter(device__is_licence=True, device__isnull=False).distinct()
        #         },
        #     },
        # }
