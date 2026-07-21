# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for ``get_device_state_data()``.

This helper is the *only* consumer of ``Record.STATE_TRANSITIONS``: it turns the
device's current state into a badge (label / colour / link) plus the list of
actions offered to the user. It has had no direct test coverage, yet it is the
piece a consolidated FSM would rewrite wholesale.

Assertions target URLs, flags and state keys rather than display labels, so they
stay valid as the translated labels evolve. The suite runs under
``LANGUAGE_CODE = "en"``, so any label that is asserted resolves to its msgid.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from dlcdb.core.models import (
    Device,
    InRoomRecord,
    LentRecord,
    LostRecord,
    Person,
    RemovedRecord,
)

ALL_ADD_PERMISSIONS = [
    "add_inroomrecord",
    "add_lentrecord",
    "add_lostrecord",
    "add_removedrecord",
    "add_orderedrecord",
]


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(email="admin@example.com", password="secret")


@pytest.fixture
def make_user(db):
    """A non-superuser carrying only the named ``core`` add-permissions."""

    def _make(*codenames, email="staff@example.com"):
        user = get_user_model().objects.create_user(email=email, password="secret")
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename))
        return get_user_model().objects.get(pk=user.pk)  # reset the perm cache

    return _make


def _targets(state_data):
    """The URLs of the offered actions."""
    return [action["url"] for action in state_data.actions]


def _offers(state_data, fragment):
    return any(fragment in url for url in _targets(state_data))


# --- No active record ----------------------------------------------------


@pytest.mark.django_db
def test_device_without_a_record_offers_only_inroom(plain_device, superuser):
    state_data = plain_device.get_state_data(user=superuser)

    assert state_data.label == "No active record"
    assert "disabled" in state_data.css_classes
    assert len(state_data.actions) == 1
    assert _offers(state_data, reverse("admin:core_inroomrecord_add"))


# --- Current-state badge -------------------------------------------------


@pytest.mark.django_db
def test_inroom_badge_shows_the_room(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert str(room.number) in state_data.label
    assert str(lentable_device.pk) in state_data.url


@pytest.mark.django_db
def test_lent_badge_shows_room_and_person(lentable_device, room, superuser):
    person = Person.objects.create(first_name="Max", last_name="Mustermann")
    record = LentRecord.objects.create(
        device=lentable_device,
        room=room,
        person=person,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert str(room.number) in state_data.label
    assert str(person) in state_data.label
    assert state_data.url == reverse("admin:core_lentrecord_change", args=[record.pk])


@pytest.mark.django_db
def test_lost_badge_is_danger_coloured(lentable_device, superuser):
    LostRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    assert "btn-danger" in lentable_device.get_state_data(user=superuser).css_classes


@pytest.mark.django_db
def test_removed_badge_is_warning_coloured(lentable_device, superuser):
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    assert "btn-warning" in lentable_device.get_state_data(user=superuser).css_classes


@pytest.mark.django_db
def test_inroom_record_without_a_room_is_flagged(lentable_device, superuser):
    """
    An INROOM record is supposed to have a room, but legacy and imported data
    does not always. The badge says so instead of blowing up.
    """
    InRoomRecord.objects.create(device=lentable_device, room=None)
    lentable_device.refresh_from_db()

    assert lentable_device.get_state_data(user=superuser).label == "Room not set!"


# --- Offered actions per state ------------------------------------------


@pytest.mark.django_db
def test_inroom_offers_move_lend_lost_and_removed(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert _offers(state_data, reverse("admin:core_inroomrecord_add"))
    assert _offers(state_data, reverse("admin:core_lostrecord_add"))
    assert _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert _offers(state_data, "lentrecord")


@pytest.mark.django_db
def test_lent_offers_return_and_lost_but_not_removal(lentable_device, room, superuser):
    """LENT -> REMOVED is not a legal transition; a lending must be ended first."""
    LentRecord.objects.create(
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert _offers(state_data, reverse("admin:core_inroomrecord_add"))
    assert _offers(state_data, reverse("admin:core_lostrecord_add"))
    assert not _offers(state_data, reverse("admin:core_removedrecord_add"))


@pytest.mark.django_db
def test_lost_offers_found_and_removal_but_not_lending(lentable_device, superuser):
    LostRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert _offers(state_data, reverse("admin:core_inroomrecord_add"))
    assert _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert not _offers(state_data, "lentrecord")


@pytest.mark.django_db
def test_removed_is_terminal_and_offers_nothing(lentable_device, superuser):
    """
    A decommissioned device is a dead end in the UI.

    Note this asserts that nothing is *offered*, not that no transition exists:
    ``restore_removed_to_lost`` (superuser bulk action) and the inventory
    "found again" flow both move devices out of REMOVED today. A consolidated
    FSM is expected to keep those legal but unsurfaced, which keeps this green.
    """
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    assert lentable_device.get_state_data(user=superuser).actions == []


# --- Permission gating ---------------------------------------------------


@pytest.mark.django_db
def test_no_user_means_no_actions(lentable_device, room):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    assert lentable_device.get_state_data(user=None).actions == []


@pytest.mark.django_db
def test_actions_are_gated_by_the_add_permission(lentable_device, room, make_user):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    user = make_user("add_lostrecord")
    state_data = lentable_device.get_state_data(user=user)

    assert _offers(state_data, reverse("admin:core_lostrecord_add"))
    assert not _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert not _offers(state_data, reverse("admin:core_inroomrecord_add"))


@pytest.mark.django_db
def test_non_lentable_devices_are_never_offered_lending(room, make_user):
    device = Device.objects.create(edv_id="EDV-NOLEND", is_lentable=False)
    InRoomRecord.objects.create(device=device, room=room)
    device.refresh_from_db()

    user = make_user(*ALL_ADD_PERMISSIONS)
    state_data = device.get_state_data(user=user)

    assert not _offers(state_data, "lentrecord")
    # ... while the other INROOM transitions stay available.
    assert _offers(state_data, reverse("admin:core_lostrecord_add"))


# --- Frontend (app_name) variants ---------------------------------------


@pytest.mark.django_db
def test_assets_rewrites_inroom_to_the_native_move_view(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser, app_name="assets")

    move = [a for a in state_data.actions if a["url"].startswith(reverse("assets:relocate"))]
    assert len(move) == 1
    assert move[0]["label"] == "Move"
    assert move[0]["external"] is False
    assert f"device={lentable_device.pk}" in move[0]["url"]


@pytest.mark.django_db
def test_assets_rewrites_lend_to_the_native_lending_view(lentable_device, room, superuser):
    record = InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser, app_name="assets")

    lend = [a for a in state_data.actions if a["label"] == "Lend"]
    assert len(lend) == 1
    assert lend[0]["url"] == reverse("lending:detail", args=[record.pk])
    assert lend[0]["external"] is False


@pytest.mark.django_db
def test_inventory_rewrites_inroom_to_the_room_inventory_view(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser, app_name="inventory")

    assert state_data.url == reverse("inventory:inventorize-room", kwargs={"pk": room.pk})


@pytest.mark.django_db
def test_admin_actions_are_marked_external(lentable_device, room, superuser):
    """
    Admin add-views require ``is_staff``; surfaces that gate on it rely on this
    flag to decide whether to render the link.
    """
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    lost = [a for a in state_data.actions if reverse("admin:core_lostrecord_add") in a["url"]]
    assert lost[0]["external"] is True


@pytest.mark.django_db
def test_actions_carry_the_device_prefill(lentable_device, room, superuser):
    """Every admin add-action prefills ``?device=<pk>`` so the form knows its target."""
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    admin_actions = [a for a in state_data.actions if a["external"]]
    assert admin_actions
    for action in admin_actions:
        assert f"device={lentable_device.pk}" in action["url"] or str(lentable_device.uuid) in action["url"]


@pytest.mark.django_db
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Known defect: the REMOVED badge links to admin:core_record_change with "
        "the *device* pk instead of the record pk (core/utils/device_methods.py), "
        "so it opens an unrelated record or 404s. Kept as xfail so it flips to "
        "green once the link is built from the record."
    ),
)
def test_removed_badge_links_to_the_removal_record(lentable_device, room, superuser):
    # Push the record pk sequence past the device pk sequence, otherwise the two
    # coincide and the assertion cannot tell the defect from correct behaviour.
    for _ in range(3):
        InRoomRecord.objects.create(device=lentable_device, room=room)

    record = RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()
    assert record.pk != lentable_device.pk, "test setup failed to diverge the pk sequences"

    state_data = lentable_device.get_state_data(user=superuser)

    assert state_data.url == reverse("admin:core_record_change", args=[record.pk])
