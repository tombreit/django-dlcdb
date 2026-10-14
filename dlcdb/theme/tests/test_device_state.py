# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for ``get_device_state_data()``.

This helper turns the device's current state into a badge (label / colour /
link) plus the list of actions offered to the user, as decided by
``lifecycle.available``.

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
from dlcdb.theme.device_state import RELOCATE_TRANSITIONS, get_device_state_data
from dlcdb.theme.navigation import with_back

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


def _form(device, name):
    """The device page's own form for state change ``name``."""
    return reverse("assets:device_transition", args=[device.pk, name])


def _urls(state_data):
    """The offered actions as {label: URL}."""
    return {action["label"]: action["url"] for action in state_data.actions}


# --- No active record ----------------------------------------------------


@pytest.mark.django_db
def test_device_without_a_record_offers_every_legal_first_step(plain_device, superuser):
    """A device with no record can be located, ordered or written off unseen.

    All three are legal from the initial state; a superuser holds every
    permission, so all three are offered.
    """
    state_data = get_device_state_data(plain_device, user=superuser)

    assert state_data.label == "No active record"
    assert "disabled" in state_data.css_classes
    assert _urls(state_data) == {
        "Locate": f"{reverse('assets:relocate')}?device={plain_device.pk}",
        "Order": reverse("assets:device_detail", args=[plain_device.pk]),
        "Remove": _form(plain_device, "remove"),
    }


@pytest.mark.django_db
def test_a_record_less_device_offers_only_what_the_user_may_do(plain_device, make_user):
    """The same device, seen by someone who may only take devices into service."""
    user = make_user("transition_can_locate_device")
    state_data = get_device_state_data(plain_device, user=user)

    assert _targets(state_data) == [f"{reverse('assets:relocate')}?device={plain_device.pk}"]


@pytest.mark.django_db
def test_order_posts_in_the_frontend_and_links_to_the_device_page_in_the_admin(plain_device, make_user):
    """The admin's device list renders the buttons inside its own form, which
    cannot hold a second one; there Order leads to the device page instead."""
    user = make_user("transition_can_order_device")

    [action] = get_device_state_data(plain_device, user=user, app_name="assets").actions
    assert action["url"] == reverse("assets:device_order", args=[plain_device.pk])
    assert action["method"] == "post"

    [action] = get_device_state_data(plain_device, user=user).actions
    assert action["url"] == reverse("assets:device_detail", args=[plain_device.pk])
    assert action["method"] == "get"


# --- Current-state badge -------------------------------------------------


@pytest.mark.django_db
def test_inroom_badge_shows_the_room(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser)

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

    state_data = get_device_state_data(lentable_device, user=superuser)

    assert str(room.number) in state_data.label
    assert str(person) in state_data.label
    assert state_data.url == reverse("admin:core_lentrecord_change", args=[record.pk])


@pytest.mark.django_db
def test_lost_badge_is_danger_coloured(lentable_device, superuser):
    establish_state(LostRecord, device=lentable_device)
    lentable_device.refresh_from_db()

    assert "btn-danger" in get_device_state_data(lentable_device, user=superuser).css_classes


@pytest.mark.django_db
def test_removed_badge_is_warning_coloured(lentable_device, superuser):
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    assert "btn-warning" in get_device_state_data(lentable_device, user=superuser).css_classes


@pytest.mark.django_db
def test_inroom_record_without_a_room_is_flagged(lentable_device, superuser):
    """
    An INROOM record is supposed to have a room, but legacy and imported data
    does not always. The badge says so instead of blowing up.
    """
    InRoomRecord.objects.create(device=lentable_device, room=None)
    lentable_device.refresh_from_db()

    assert get_device_state_data(lentable_device, user=superuser).label == "Room not set!"


# --- Offered actions per state ------------------------------------------


@pytest.mark.django_db
def test_inroom_offers_move_lend_lost_and_removed(lentable_device, room, superuser):
    record = InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser)

    assert _urls(state_data) == {
        "Move": f"{reverse('assets:relocate')}?device={lentable_device.pk}",
        "Lend": reverse("lending:detail", args=[record.pk]),
        "Not locatable": _form(lentable_device, "lose"),
        "Remove": _form(lentable_device, "remove"),
    }


@pytest.mark.django_db
def test_lent_offers_return_loss_and_removal(lentable_device, room, superuser):
    """Decommissioning a device while it is on loan is legal, so it is offered.

    The return goes to the lending form rather than the Move module: a return
    stamps the lending's end date first and only then puts the device back, which
    a move on its own would not do.
    """
    record = establish_state(
        LentRecord,
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser)

    assert _urls(state_data) == {
        "Return": f"{reverse('lending:detail', args=[record.pk])}?flow=return",
        "Not locatable": _form(lentable_device, "lose"),
        "Remove": _form(lentable_device, "remove"),
    }


@pytest.mark.django_db
def test_lost_offers_found_removal_and_re_marking_but_not_lending(lentable_device, superuser):
    establish_state(LostRecord, device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser)

    assert _offers(state_data, reverse("assets:relocate"))  # Found
    assert _offers(state_data, _form(lentable_device, "remove"))
    assert not _offers(state_data, "lending")
    # LOST -> LOST is legal, so an inventory can re-mark a device that is still
    # missing. Whether that is worth a button is now the operator's call, made by
    # granting transition_can_lose_device -- not something the state machine decides.
    assert _offers(state_data, _form(lentable_device, "lose"))


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

    state_data = get_device_state_data(lentable_device, user=superuser)

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

    assert get_device_state_data(lentable_device, user=user).actions == []


# --- Permission gating ---------------------------------------------------


@pytest.mark.django_db
def test_no_user_means_no_actions(lentable_device, room):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    assert get_device_state_data(lentable_device, user=None).actions == []


@pytest.mark.django_db
def test_actions_are_gated_by_the_transition_permission(lentable_device, room, make_user):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    user = make_user("transition_can_lose_device")
    state_data = get_device_state_data(lentable_device, user=user)

    assert _targets(state_data) == [_form(lentable_device, "lose")]


@pytest.mark.django_db
def test_one_permission_covers_both_lending_and_returning(lentable_device, room, make_user):
    """``transition_can_lend_device`` is the whole lending competence, both directions."""
    user = make_user("transition_can_lend_device")

    record = InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()
    assert [a["label"] for a in get_device_state_data(lentable_device, user=user).actions] == ["Lend"]

    lending = establish_state(
        LentRecord,
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    lentable_device.refresh_from_db()
    assert [a["label"] for a in get_device_state_data(lentable_device, user=user).actions] == ["Return"]
    assert record.pk != lending.pk


@pytest.mark.django_db
def test_non_lentable_devices_are_never_offered_lending(room, make_user):
    device = Device.objects.create(edv_id="EDV-NOLEND", is_lentable=False)
    InRoomRecord.objects.create(device=device, room=room)
    device.refresh_from_db()

    user = make_user(*ALL_LIFECYCLE_PERMISSIONS)
    state_data = get_device_state_data(device, user=user)

    assert not _offers(state_data, "lending")
    # ... while the other INROOM transitions stay available.
    assert _offers(state_data, _form(device, "lose"))


# --- Frontend (app_name) variants ---------------------------------------


@pytest.mark.django_db
def test_assets_rewrites_inroom_to_the_native_move_view(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="assets")

    move = [a for a in state_data.actions if a["url"].startswith(reverse("assets:relocate"))]
    assert len(move) == 1
    assert move[0]["label"] == "Move"
    assert f"device={lentable_device.pk}" in move[0]["url"]


@pytest.mark.django_db
def test_assets_rewrites_lend_to_the_native_lending_view(lentable_device, room, superuser):
    record = InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="assets")

    lend = [a for a in state_data.actions if a["label"] == "Lend"]
    assert len(lend) == 1
    assert lend[0]["url"] == reverse("lending:detail", args=[record.pk])


@pytest.mark.django_db
def test_assets_keeps_each_move_labelled_as_itself(lentable_device, room, superuser):
    """Routing is by transition name, so the moves that end in a room keep their
    own labels instead of all reading "Move"."""
    establish_state(LostRecord, device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="assets")

    found = [a for a in state_data.actions if a["url"].startswith(reverse("assets:relocate"))]
    assert len(found) == 1
    assert found[0]["label"] == "Found"


def test_frontend_move_routing_matches_the_localisation_declaration():
    """The buttons routed to the Move module are exactly the moves it performs.

    ``device_state`` decides which actions link to ``assets:relocate``; the
    module's picker and ``relocate_device`` are built from
    ``lifecycle.LOCALISING_MOVES``. If the two ever diverge the result is a
    button that the view then refuses, which is how ``recover`` first went wrong.
    """
    assert RELOCATE_TRANSITIONS == set(lifecycle.LOCALISING_MOVES)
    assert "recover" not in RELOCATE_TRANSITIONS


@pytest.mark.django_db
def test_recovery_does_not_route_into_the_move_module(lentable_device, superuser):
    """The Move module's picker excludes REMOVED devices.

    ``assets.pickers.MOVEABLE_RECORD_TYPES`` restates the moveable states by
    hand, so sending a recovery there yields a form that rejects the device
    ("not a valid choice"). Recovery has its own form on the device page
    instead. If that picker is ever derived from the transition table, this can
    move back into the Move module.
    """
    RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="assets")

    recover = [a for a in state_data.actions if a["label"] == "Recover"]
    assert len(recover) == 1
    assert recover[0]["url"] == reverse("assets:device_transition", args=[lentable_device.pk, "recover"])
    assert not _offers(state_data, reverse("assets:relocate"))


@pytest.mark.django_db
def test_assets_routes_the_other_state_changes_to_the_device_page_forms(lentable_device, room, superuser):
    """Not locatable and Remove have no screen of their own; the device page's
    forms serve them, so no assets action leads into the admin."""
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="assets")

    for name in ("lose", "remove"):
        assert _offers(state_data, reverse("assets:device_transition", args=[lentable_device.pk, name]))
    assert not _offers(state_data, "/admin/")


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

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="assets")

    returns = [a for a in state_data.actions if a["label"] == "Return"]
    assert len(returns) == 1
    # Same return screen the lending list's "Return" button opens.
    assert returns[0]["url"] == f"{reverse('lending:detail', args=[record.pk])}?flow=return"
    assert not _offers(state_data, reverse("assets:relocate"))


@pytest.mark.django_db
def test_inventory_rewrites_inroom_to_the_room_inventory_view(lentable_device, room, superuser):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    state_data = get_device_state_data(lentable_device, user=superuser, app_name="inventory")

    assert state_data.url == reverse("inventory:inventorize-room", kwargs={"pk": room.pk})


@pytest.mark.django_db
def test_inventory_offers_the_same_frontend_screens_as_the_device_page(lentable_device, plain_device, room, superuser):
    """No state change in the inventory search leads into the admin; Order posts."""
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    for device in (lentable_device, plain_device):
        inventory = get_device_state_data(device, user=superuser, app_name="inventory")
        assert inventory.actions == get_device_state_data(device, user=superuser, app_name="assets").actions
        assert not _offers(inventory, "/admin/")

    [order] = [
        a
        for a in get_device_state_data(plain_device, user=superuser, app_name="inventory").actions
        if a["label"] == "Order"
    ]
    assert order["method"] == "post"


@pytest.mark.django_db
def test_the_device_page_forms_and_order_return_to_the_back_url(plain_device, superuser):
    """The inventory search passes its own URL; Move keeps its own landing page."""
    back = "/inventory/devices/?q=EDV"

    actions = get_device_state_data(plain_device, user=superuser, app_name="inventory", back=back).actions
    urls = {action["label"]: action["url"] for action in actions}

    assert urls["Order"] == with_back(reverse("assets:device_order", args=[plain_device.pk]), back)
    assert urls["Remove"] == with_back(reverse("assets:device_transition", args=[plain_device.pk, "remove"]), back)
    assert "back=" not in urls["Locate"]


@pytest.mark.django_db
def test_frontend_badges_link_to_the_device_page_for_its_viewers(lentable_device, plain_device, room, make_user):
    """A lent or lost device's badge opens the device page, not the admin, and
    only for users who may see it."""
    establish_state(
        LentRecord,
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    establish_state(LostRecord, device=plain_device)
    viewer = make_user("view_device")
    other = get_user_model().objects.create_user(email="other@example.com", username="other", password="secret")

    for device in (lentable_device, plain_device):
        device.refresh_from_db()
        assert get_device_state_data(device, user=viewer, app_name="inventory").url == reverse(
            "assets:device_detail", args=[device.pk]
        )
        assert get_device_state_data(device, user=other, app_name="inventory").url == ""
        # The admin keeps its own pages.
        assert get_device_state_data(device, user=viewer).url.startswith("/admin/")


@pytest.mark.django_db
def test_removed_badge_links_to_the_removal_record(lentable_device, room, superuser):
    # Push the record pk sequence past the device pk sequence, otherwise the two
    # coincide and the assertion cannot tell the defect from correct behaviour.
    for _ in range(3):
        InRoomRecord.objects.create(device=lentable_device, room=room)

    record = RemovedRecord.objects.create(device=lentable_device)
    lentable_device.refresh_from_db()
    assert record.pk != lentable_device.pk, "test setup failed to diverge the pk sequences"

    state_data = get_device_state_data(lentable_device, user=superuser)

    assert state_data.url == reverse("admin:core_record_change", args=[record.pk])
