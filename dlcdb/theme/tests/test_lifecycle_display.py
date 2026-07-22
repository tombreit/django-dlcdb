# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the decorative half of the lifecycle: the state badge colours, which
live in the theme app (the states themselves live in dlcdb.core.lifecycle).
"""

import pytest

from dlcdb.core.models.record import RECORD_TYPE_KEYS
from dlcdb.theme.lifecycle_display import STATE_COLORS, state_color


def test_colour_map_covers_every_state():
    assert set(STATE_COLORS) == set(RECORD_TYPE_KEYS)


@pytest.mark.parametrize("key", RECORD_TYPE_KEYS)
def test_state_color_matches_the_map(key):
    assert state_color(key) == STATE_COLORS[key]


def test_state_color_falls_back_for_unknown_states():
    assert state_color("NO_SUCH_STATE") == "secondary"
