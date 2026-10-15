# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dlcdb.core.admin.base_admin import get_has_note_badge
from dlcdb.theme.icons import get_icon_for_class


def test_known_model_has_its_icon_and_an_unknown_one_none():
    assert get_icon_for_class("core.room") == "bi bi-door-open"
    assert get_icon_for_class("core.nosuchmodel") == ""


def test_a_device_has_the_navbar_icon_and_lost_its_own():
    """A device looks the same in the navbar, the tiles and the search; Lost is not a Records lookalike."""
    assert get_icon_for_class("core.device") == "bi bi-pc-display"
    assert get_icon_for_class("core.lostrecord") == "bi bi-question-circle"
    assert get_icon_for_class("core.lostrecord") != get_icon_for_class("core.record")


def test_note_badge_shows_the_model_icon():
    assert "bi bi-door-open" in get_has_note_badge(obj_type="core.room", has_note=True)
