# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters used by the room overview."""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Room
from dlcdb.theme.filters import HAS_NOTE_CHOICES, filter_boolean_choice, filter_has_note


class RoomFilter(django_filters.FilterSet):
    """Search and the filters from the previous Room changelist."""

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    is_auto_return_room = django_filters.ChoiceFilter(
        choices=[("true", _("Auto-return room")), ("false", _("No auto-return room"))],
        method=filter_boolean_choice,
        label=_("Auto return"),
        empty_label=_("Any auto-return status..."),
    )
    is_external = django_filters.ChoiceFilter(
        choices=[("true", _("External room")), ("false", _("Not external"))],
        method=filter_boolean_choice,
        label=_("External"),
        empty_label=_("Any external status..."),
    )
    has_note = django_filters.ChoiceFilter(
        choices=HAS_NOTE_CHOICES,
        method=filter_has_note,
        label=_("Note"),
        empty_label=_("Any note status..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("number", "number"),
            ("nickname", "nickname"),
            ("assets_count", "assets"),
            ("modified_at", "modified"),
            ("created_at", "created"),
        ),
        # Keyed by model field name, not by the exposed parameter.
        field_labels={"created_at": _("Created")},
    )

    class Meta:
        model = Room
        fields = [
            "search",
            "is_auto_return_room",
            "is_external",
            "has_note",
            "ordering",
        ]

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(number__icontains=value)
            | Q(nickname__icontains=value)
            | Q(description__icontains=value)
            | Q(note__icontains=value)
        )
