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

from dlcdb.core import lifecycle
from dlcdb.core.models import (
    Device,
    InRoomRecord,
    LentRecord,
    LostRecord,
    Person,
    RemovedRecord,
)
from dlcdb.core.tests.testingutils import establish_state

ALL_LIFECYCLE_PERMISSIONS = [
    "transition_can_order_device",
    "transition_can_locate_device",
    "transition_can_relocate_device",
    "transition_can_lend_device",
    "transition_can_lose_device",
    "transition_can_find_device",
    "transition_can_remove_device",
    "transition_can_restore_device",
    "transition_can_recover_device",
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
def test_device_without_a_record_offers_every_legal_first_step(plain_device, superuser):
    """A device with no record can be located, ordered or written off unseen.

    All three are legal from the initial state; a superuser holds every
    permission, so all three are offered.
    """
    state_data = plain_device.get_state_data(user=superuser)

    assert state_data.label == "No active record"
    assert "disabled" in state_data.css_classes
    assert _offers(state_data, reverse("admin:core_inroomrecord_add"))
    assert _offers(state_data, reverse("admin:core_orderedrecord_add"))
    assert _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert len(state_data.actions) == 3


@pytest.mark.django_db
def test_a_record_less_device_offers_only_what_the_user_may_do(plain_device, make_user):
    """The same device, seen by someone who may only take devices into service."""
    user = make_user("transition_can_locate_device")
    state_data = plain_device.get_state_data(user=user)

    assert _targets(state_data) == [f"{reverse('admin:core_inroomrecord_add')}?device={plain_device.pk}"]


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
    record = establish_state(
        LentRecord,
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
    establish_state(LostRecord, device=lentable_device)
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
def test_lent_offers_return_loss_and_removal(lentable_device, room, superuser):
    """Decommissioning a device while it is on loan is legal, so it is offered.

    The return goes to the lending form rather than an InRoomRecord add-view: a
    return stamps the lending's end date first and only then puts the device
    back, which creating a room record on its own would not do.
    """
    record = establish_state(
        LentRecord,
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert _offers(state_data, reverse("admin:core_lentrecord_change", args=[record.pk]))
    assert _offers(state_data, reverse("admin:core_lostrecord_add"))
    assert _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert not _offers(state_data, reverse("admin:core_inroomrecord_add"))


@pytest.mark.django_db
def test_lost_offers_found_removal_and_re_marking_but_not_lending(lentable_device, superuser):
    establish_state(LostRecord, device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    assert _offers(state_data, reverse("admin:core_inroomrecord_add"))
    assert _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert not _offers(state_data, "lentrecord")
    # LOST -> LOST is legal, so an inventory can re-mark a device that is still
    # missing. Whether that is worth a button is now the operator's call, made by
    # granting transition_can_lose_device -- not something the state machine decides.
    assert _offers(state_data, reverse("admin:core_lostrecord_add"))


@pytest.mark.django_db
def test_removed_offers_the_two_ways_back_to_a_holder_of_both(lentable_device, superuser):
    """A decommissioned device is no longer a hardcoded dead end.

    ``restore`` and ``recover`` were always legal -- the superuser bulk action
    and the inventory "found again" flow both used them -- but nothing surfaced
    them. They are now offered to whoever holds their permissions, which ship
    granted to nobody (see ``test_removed_is_still_a_dead_end_for_ordinary_users``).
    """
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser)

    labels = {action["label"] for action in state_data.actions}
    assert labels == {"Restore", "Recover"}


@pytest.mark.django_db
def test_removed_is_still_a_dead_end_for_ordinary_users(lentable_device, make_user):
    """The case the old ``add_<target proxy>`` derivation could not express.

    ``recover`` writes an InRoomRecord and ``restore`` a LostRecord, so they used
    to be gated by the very permissions an ordinary inventory user needs for
    everyday work. Now someone who may move and lose devices still cannot bring a
    decommissioned one back.
    """
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    user = make_user("transition_can_relocate_device", "transition_can_lose_device", "transition_can_find_device")

    assert lentable_device.get_state_data(user=user).actions == []


# --- Permission gating ---------------------------------------------------


@pytest.mark.django_db
def test_no_user_means_no_actions(lentable_device, room):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    assert lentable_device.get_state_data(user=None).actions == []


@pytest.mark.django_db
def test_actions_are_gated_by_the_transition_permission(lentable_device, room, make_user):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    user = make_user("transition_can_lose_device")
    state_data = lentable_device.get_state_data(user=user)

    assert _offers(state_data, reverse("admin:core_lostrecord_add"))
    assert not _offers(state_data, reverse("admin:core_removedrecord_add"))
    assert not _offers(state_data, reverse("admin:core_inroomrecord_add"))


@pytest.mark.django_db
def test_one_permission_covers_both_lending_and_returning(lentable_device, room, make_user):
    """``transition_can_lend_device`` is the whole lending competence, both directions."""
    user = make_user("transition_can_lend_device")

    record = InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()
    assert [a["label"] for a in lentable_device.get_state_data(user=user).actions] == ["Lend"]

    lending = establish_state(
        LentRecord,
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()
    assert [a["label"] for a in lentable_device.get_state_data(user=user).actions] == ["Return"]
    assert record.pk != lending.pk


@pytest.mark.django_db
def test_non_lentable_devices_are_never_offered_lending(room, make_user):
    device = Device.objects.create(edv_id="EDV-NOLEND", is_lentable=False)
    InRoomRecord.objects.create(device=device, room=room)
    device.refresh_from_db()

    user = make_user(*ALL_LIFECYCLE_PERMISSIONS)
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
def test_assets_keeps_each_move_labelled_as_itself(lentable_device, room, superuser):
    """Routing is by transition name, so the moves that end in a room keep their
    own labels instead of all reading "Move"."""
    establish_state(LostRecord, device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser, app_name="assets")

    found = [a for a in state_data.actions if a["url"].startswith(reverse("assets:relocate"))]
    assert len(found) == 1
    assert found[0]["label"] == "Found"
    assert found[0]["external"] is False


def test_frontend_move_routing_matches_the_localisation_declaration():
    """The buttons routed to the Move module are exactly the moves it performs.

    ``device_methods`` decides which actions link to ``assets:relocate``; the
    module's picker and ``relocate_device`` are built from
    ``lifecycle.LOCALISING_MOVES``. If the two ever diverge the result is a
    button that the view then refuses, which is how ``recover`` first went wrong.
    """
    from dlcdb.core.utils.device_methods import RELOCATE_TRANSITIONS

    assert RELOCATE_TRANSITIONS == set(lifecycle.LOCALISING_MOVES)
    assert "recover" not in RELOCATE_TRANSITIONS


@pytest.mark.django_db
def test_recovery_does_not_route_into_the_move_module(lentable_device, superuser):
    """The Move module's picker excludes REMOVED devices.

    ``assets.pickers.MOVEABLE_RECORD_TYPES`` restates the moveable states by
    hand, so sending a recovery there yields a form that rejects the device
    ("not a valid choice"). Recovery goes to the admin add-view instead, which
    the lifecycle accepts. If that picker is ever derived from the transition
    table, this can move back into the Move module.
    """
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser, app_name="assets")

    recover = [a for a in state_data.actions if a["label"] == "Recover"]
    assert len(recover) == 1
    assert recover[0]["url"].startswith(reverse("admin:core_inroomrecord_add"))
    assert recover[0]["external"] is True
    assert not _offers(state_data, reverse("assets:relocate"))


@pytest.mark.django_db
def test_assets_routes_a_return_to_the_lending_form(lentable_device, room, superuser):
    """A return is not a relocation -- it must not land in the "Move" module."""
    record = establish_state(
        LentRecord,
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()

    state_data = lentable_device.get_state_data(user=superuser, app_name="assets")

    returns = [a for a in state_data.actions if a["label"] == "Return"]
    assert len(returns) == 1
    # Same return screen the lending list's "Return" button opens.
    assert returns[0]["url"] == f"{reverse('lending:detail', args=[record.pk])}?flow=return"
    assert returns[0]["external"] is False
    assert not _offers(state_data, reverse("assets:relocate"))


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
