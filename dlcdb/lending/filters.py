# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import LentRecord, Record, DeviceType, Person

# Lending state keys. This filter is the single source of truth for lending
# state in the standalone lending app; it intentionally does not import from
# dlcdb/core/admin/, as the admin interface is being phased out.
STATE_OVERDUE = "overdue"
STATE_LENT = "lent"
STATE_AVAILABLE = "available"

STATE_CHOICES = [
    (STATE_OVERDUE, _("Overdue")),
    (STATE_LENT, _("Lent")),
    (STATE_AVAILABLE, _("Available")),
]


def current_borrowers(request):
    """
    Persons who currently have an active lent record, scoped to the request's
    tenant. Used to keep the person filter dropdown compact and relevant.
    """
    qs = Person.objects.filter(record__record_type=Record.LENT, record__is_active=True)
    tenant = getattr(request, "tenant", None) if request else None
    if tenant:
        qs = qs.filter(record__device__tenant=tenant)
    return qs.distinct().order_by("last_name", "first_name")


class LentRecordFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter_method")

    state = django_filters.ChoiceFilter(
        method="state_filter_method",
        choices=STATE_CHOICES,
        label=_("State"),
        empty_label=_("Any state..."),
    )

    device__device_type = django_filters.ModelChoiceFilter(
        queryset=DeviceType.objects.filter(device__is_lentable=True).distinct(),
        label=_("Type"),
        empty_label=_("Device type..."),
    )

    person = django_filters.ModelChoiceFilter(
        queryset=current_borrowers,
        label=_("Person"),
        empty_label=_("Person..."),
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ("device__edv_id", "device"),
            ("person__last_name", "person"),
            ("room__number", "room"),
            ("lent_desired_end_date", "due"),
            ("modified_at", "modified"),
        ),
    )

    class Meta:
        model = LentRecord
        fields = ["search", "state", "device__device_type", "person", "ordering"]

    def search_filter_method(self, queryset, name, value):
        return queryset.filter(
            Q(device__edv_id__icontains=value)
            | Q(device__sap_id__icontains=value)
            | Q(device__manufacturer__name__icontains=value)
            | Q(device__series__icontains=value)
            | Q(person__first_name__icontains=value)
            | Q(person__last_name__icontains=value)
            | Q(person__email__icontains=value)
            | Q(lent_note__icontains=value)
            | Q(lent_accessories__icontains=value)
        )

    def state_filter_method(self, queryset, name, value):
        if value == STATE_OVERDUE:
            return queryset.filter(
                lent_desired_end_date__lte=datetime.date.today(),
                lent_end_date__isnull=True,
            )
        elif value == STATE_LENT:
            return queryset.filter(record_type=Record.LENT)
        elif value == STATE_AVAILABLE:
            return queryset.filter(record_type=Record.INROOM)
        return queryset


class LendingPersonFilter(django_filters.FilterSet):
    """
    Live-search filter backing the person picker on the lending detail view.
    Searches all persons by name/email; an empty query returns nothing (so the
    picker starts blank) and "*" returns everyone.
    """

    search = django_filters.CharFilter(method="search_method", label=_("Search"))

    class Meta:
        model = Person
        fields = ["search"]

    def search_method(self, queryset, name, value):
        qs = Person.objects.order_by("last_name", "first_name")

        if not value:
            return Person.objects.none()
        if value == "*":
            return qs
        return qs.filter(Q(first_name__icontains=value) | Q(last_name__icontains=value) | Q(email__icontains=value))
