import django_filters
from django.db.models import Q

from ..core.models import Room
from .forms import RoomSearchForm


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
