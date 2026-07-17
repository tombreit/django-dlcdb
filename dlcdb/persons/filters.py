# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters used by the person overview."""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import OrganizationalUnit, Person


class PersonFilter(django_filters.FilterSet):
    """Search and the filters from the previous Person changelist."""

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    organizational_unit = django_filters.ModelChoiceFilter(
        queryset=OrganizationalUnit.objects.all(),
        label=_("Organizational unit"),
        empty_label=_("Any organizational unit..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("last_name", "name"),
            ("email", "email"),
            ("organizational_unit__name", "unit"),
            ("modified_at", "modified"),
        ),
    )

    class Meta:
        model = Person
        fields = [
            "search",
            "organizational_unit",
            "ordering",
        ]

    def search_filter(self, queryset, name, value):
        # Mirrors the admin's search_fields, including the UDB-mirrored names.
        return queryset.filter(
            Q(last_name__icontains=value)
            | Q(first_name__icontains=value)
            | Q(email__icontains=value)
            | Q(udb_person_last_name__icontains=value)
            | Q(udb_person_first_name__icontains=value)
            | Q(udb_person_email_internal_business__icontains=value)
        )
