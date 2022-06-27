from django.db.models import Q

import django_filters

from dlcdb.core.models import Person


class PersonFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='custom_user_search',label="Search")

    class Meta:
        model = Person
        fields = [
            # 'first_name',
            # 'last_name',
            'q'
        ]

    def custom_user_search(self, queryset, name, value):
        return Person.objects.filter(
            Q(first_name__icontains=value) | 
            Q(last_name__icontains=value) | 
            Q(email__icontains=value)
        )