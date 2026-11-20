# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters used by the person overview."""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit, Person, Room


class PersonFilter(django_filters.FilterSet):
    """Search and the filters from the previous Person changelist."""

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    organizational_unit = django_filters.ModelChoiceFilter(
        queryset=OrganizationalUnit.objects.all(),
        label=_("Organizational unit"),
        empty_label=_("Any organizational unit..."),
    )
    organizational_positions = django_filters.ModelChoiceFilter(
        queryset=OrganizationalPosition.objects.all(),
        label=_("Position"),
        empty_label=_("Any position..."),
    )
    room = django_filters.ModelChoiceFilter(
        queryset=Room.objects.all(),
        label=_("Room"),
        empty_label=_("Any room..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("last_name", "name"),
            ("email", "email"),
            ("organizational_unit__name", "unit"),
            ("room__number", "room"),
            ("modified_at", "modified"),
            ("created_at", "created"),
        ),
        # Keyed by model field name, not by the exposed parameter.
        field_labels={"organizational_unit__name": _("Organizational unit"), "created_at": _("Created")},
    )

    class Meta:
        model = Person
        fields = [
            "search",
            "organizational_unit",
            "organizational_positions",
            "room",
            "ordering",
        ]

    def search_filter(self, queryset, name, value):
        # The admin's search_fields, including the UDB-mirrored names, and the
        # room number. Not in Person.search_q: the person pickers share that.
        return queryset.filter(
            Person.search_q(value)
            | Q(room__number__icontains=value)
            | Q(udb_person_last_name__icontains=value)
            | Q(udb_person_first_name__icontains=value)
            | Q(udb_person_email_internal_business__icontains=value)
        )
