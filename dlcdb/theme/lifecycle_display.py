# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Presentation for the device lifecycle: the Bootstrap contextual colour of each
state's badge.

This is the deliberately "decorative" half of the lifecycle. The states,
transitions and their keys live in ``dlcdb.core.lifecycle`` (the source of
truth); only the colours -- a pure view concern -- live here, in the theme app.
Keyed by the same state keys so the two cannot drift.

Views attach a colour to their querysets with ``active_record_color_case()`` (a
DB annotation, so it works cheaply over a list) and templates render
``text-bg-{{ ... }}``; per project convention there is no template tag.
"""

from django.db.models import Case, CharField, Value, When

from dlcdb.core import lifecycle

# Bootstrap contextual colour per state key.
STATE_COLORS = {
    lifecycle.ORDERED: "info",
    lifecycle.INROOM: "success",
    lifecycle.LENT: "warning",
    lifecycle.LOST: "danger",
    lifecycle.REMOVED: "secondary",
}

# Fallback for an unknown/empty state.
DEFAULT_COLOR = "secondary"


def state_color(record_type):
    """The badge colour for a state key (scalar helper, e.g. for a single object)."""
    return STATE_COLORS.get(record_type, DEFAULT_COLOR)


def active_record_color_case(field="active_record__record_type"):
    """A ``Case()`` mapping a device's active ``record_type`` to its badge colour,
    for ``.annotate(state_color=active_record_color_case())`` on a Device queryset."""
    whens = [When(**{field: key}, then=Value(color)) for key, color in STATE_COLORS.items()]
    return Case(*whens, default=Value(DEFAULT_COLOR), output_field=CharField())
