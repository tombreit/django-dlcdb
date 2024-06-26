# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db.models import Q

import django_filters

from dlcdb.core.models import Person


class PersonFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="custom_user_search", label="Search")

    class Meta:
        model = Person
        fields = [
            # 'first_name',
            # 'last_name',
            "search"
        ]

    def custom_user_search(self, queryset, name, value):
        """
        Only allow current contracts to get some things.
        """

        # qs = (
        #     Person.active_contract_objects
        #     .annotate(assignments_count=Count('assignedthing__pk'))
        #     .order_by("-assignments_count")  # .order_by("-assignedthing")
        # )

        qs = Person.smallstuff_person_objects.order_by("-assigned_things_count")

        if not value:
            qs = Person.objects.none()
        elif value == "*":
            qs = qs
        else:
            qs = qs.filter(Q(first_name__icontains=value) | Q(last_name__icontains=value) | Q(email__icontains=value))

        return qs
