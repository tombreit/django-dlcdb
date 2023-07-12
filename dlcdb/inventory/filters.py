import django_filters
from django.db.models import Q

from ..core.models import Room, Device, DeviceType, Record
from .forms import RoomSearchForm, DeviceSearchForm


class RoomFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='string_search_filter', label="Search rooms")

    def string_search_filter(self, queryset, name, value):
        return Room.inventory_objects.get_tenant_aware_objects(self.request.tenant).filter(
            Q(number__icontains=value) | 
            Q(nickname__icontains=value) | 
            Q(description__icontains=value)
        )

    class Meta:
        model = Room
        form = RoomSearchForm
        fields = ['q']


class DeviceFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='string_search_filter', label="Search devices")
    device_type = django_filters.ModelChoiceFilter(queryset=DeviceType.objects.all(), label="Geräteklasse")
    record = django_filters.ChoiceFilter(field_name="active_record__record_type", choices=Record.RECORD_TYPE_CHOICES, label="Record")


    def string_search_filter(self, queryset, name, value):
        return self.queryset.filter(
            Q(edv_id__icontains=value) | 
            Q(sap_id__icontains=value) | 
            Q(series__icontains=value) |
            Q(manufacturer__name__icontains=value)
        )

    class Meta:
        model = Device
        form = DeviceSearchForm
        fields = [
            # 'device_type',
            # 'active_record__record_type',
        ]
