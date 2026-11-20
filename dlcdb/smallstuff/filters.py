# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import django_filters
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Person
from dlcdb.theme.pickers import picker_filter


class PersonFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="custom_user_search", label=_("Search"))

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

        qs = Person.smallstuff_person_objects.order_by("-assigned_things_count").prefetch_related(
            "organizational_positions"
        )
        return picker_filter(qs, value, Person.search_q(value))
