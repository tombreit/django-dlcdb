from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class IsAssignedFilter(SimpleListFilter):
    title = 'Is assigned?'
    parameter_name = 'is_assigned'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Yes'),
            ('No', 'No'),
        )

    def queryset(self, request, queryset):
        value = self.value()

        is_assigned_filter = Q(
            Q(person__isnull=False) |
            Q(assigned_device__isnull=False)
        )

        if value == 'Yes':
            return queryset.filter(
                is_assigned_filter
            )
        elif value == 'No':
            return queryset.exclude(
                is_assigned_filter
            )

        return queryset


class LicenceTypeListFilter(SimpleListFilter):
    title = _('Licence type')
    parameter_name = 'licence_type'

    def lookups(self, request, model_admin):
        from dlcdb.core.models import Device
        # lookups expects a tuple of two-tuples -> tuple()
        # eleminate duplicates from list of tuples -> set()
        licence_types = tuple(set(
            Device.objects.filter(is_licence=True).distinct().values_list('device_type__id', 'device_type__name')
        ))
        return licence_types

    def queryset(self, request, queryset):
        return queryset.filter(device__device_type=self.value()) if self.value() else queryset
