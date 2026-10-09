# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Filter methods shared by the FilterSets of the list pages. They are plain
functions for django-filter's ``method=``, which accepts a callable as well as
a method name. django-filter never calls a method with an empty value, so none
of them guards against one.

Spelled as ChoiceFilters, not BooleanFilters: the filterbar renders only
choice-ish filters, so a BooleanFilter would show up as no dropdown at all.
"""

from django.utils.translation import gettext_lazy as _

HAS_NOTE_CHOICES = [("has_note", _("Has note")), ("has_no_note", _("No note"))]


def filter_boolean_choice(queryset, name, value):
    """``("true", ...)`` / ``("false", ...)`` choices on the boolean field ``name``."""
    return queryset.filter(**{name: value == "true"})


def filter_has_note(queryset, name, value):
    """Same semantics as the admin's HasNoteFilter: an empty ``note`` is "no note"."""
    if value == "has_note":
        return queryset.exclude(note__exact="")
    return queryset.filter(note__exact="")
