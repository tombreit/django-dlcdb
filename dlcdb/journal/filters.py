# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters used by the journal list."""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import JournalEntry


def _distinct_values(field):
    """The values ``field`` has in the journal, as choices. Source and event are
    free text, so the filter offers whatever the emitters have written."""
    values = JournalEntry.objects.order_by(field).values_list(field, flat=True).distinct()
    return [(value, value) for value in values]


class JournalEntryFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    source = django_filters.ChoiceFilter(
        label=_("Source"),
        empty_label=_("Any source..."),
    )
    event = django_filters.ChoiceFilter(
        label=_("Event"),
        empty_label=_("Any event..."),
    )
    level = django_filters.ChoiceFilter(
        choices=JournalEntry.Level.choices,
        method="minimum_level_filter",
        label=_("Minimum level"),
        empty_label=_("Any level..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("timestamp", "timestamp"),
            ("source", "source"),
            ("level", "level"),
        ),
        # Keyed by model field name, not by the exposed parameter.
        field_labels={"timestamp": _("Time")},
    )

    class Meta:
        model = JournalEntry
        fields = ["search", "source", "event", "level", "ordering"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["source"].extra["choices"] = _distinct_values("source")
        self.filters["event"].extra["choices"] = _distinct_values("event")

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(summary__icontains=value)
            | Q(body__icontains=value)
            | Q(username__icontains=value)
            | Q(object_repr__icontains=value)
            | Q(source__icontains=value)
        )

    def minimum_level_filter(self, queryset, name, value):
        # Lower levels are more severe: "Warning" means warnings and worse.
        return queryset.filter(level__lte=int(value)) if value else queryset
