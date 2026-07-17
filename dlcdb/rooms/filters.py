# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters used by the room overview."""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Room


class RoomFilter(django_filters.FilterSet):
    """Search and the filters from the previous Room changelist."""

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    is_auto_return_room = django_filters.ChoiceFilter(
        choices=[("true", _("Auto-return room")), ("false", _("No auto-return room"))],
        method="boolean_choice_filter",
        label=_("Auto return"),
        empty_label=_("Any auto-return status..."),
    )
    is_external = django_filters.ChoiceFilter(
        choices=[("true", _("External room")), ("false", _("Not external"))],
        method="boolean_choice_filter",
        label=_("External"),
        empty_label=_("Any external status..."),
    )
    has_note = django_filters.ChoiceFilter(
        choices=[("has_note", _("Has note")), ("has_no_note", _("No note"))],
        method="note_filter",
        label=_("Note"),
        empty_label=_("Any note status..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("number", "number"),
            ("nickname", "nickname"),
            ("assets_count", "assets"),
            ("modified_at", "modified"),
        ),
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

    def boolean_choice_filter(self, queryset, name, value):
        return queryset.filter(**{name: value == "true"}) if value else queryset

    def note_filter(self, queryset, name, value):
        # Same semantics as the admin's HasNoteFilter.
        if value == "has_note":
            return queryset.exclude(note__exact="")
        if value == "has_no_note":
            return queryset.filter(note__exact="")
        return queryset
