# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Unit tests for the lifecycle module itself -- the states, the transition table,
and the enforcement it drives.
"""

import pytest

from dlcdb.core import lifecycle
from dlcdb.core.models import InRoomRecord, LentRecord, Record, Room


# --- The module is the whole picture ------------------------------------


def test_every_transition_has_a_function_and_vice_versa():
    """
    The point of the module: one ``transition_<name>`` function per table row,
    no more, no less. If they drift apart, the module stops being the complete,
    readable lifecycle -- so pin the 1:1 correspondence.
    """
    expected = {f"transition_{t.name}" for t in lifecycle.TRANSITIONS}
    actual = {name for name in dir(lifecycle) if name.startswith("transition_")}
    assert expected == actual


def test_every_state_maps_to_a_proxy_model():
    for key in lifecycle.RECORD_TYPE_KEYS:
        proxy = lifecycle.proxy_for(key)
        assert proxy._meta.proxy
        assert issubclass(proxy, Record)


def test_every_state_is_reachable():
    """Every non-initial state is the target of at least one transition."""
    targets = {t.target for t in lifecycle.TRANSITIONS}
    assert set(lifecycle.RECORD_TYPE_KEYS) <= targets


def test_transition_targets_are_valid_states():
    for t in lifecycle.TRANSITIONS:
        assert t.target in lifecycle.STATES
        for source in t.sources:
            assert source is None or source in lifecycle.STATES


# --- can_transition matrix ----------------------------------------------

# The complete legality graph, written out by hand rather than derived from
# ``TRANSITIONS`` -- a test that computes its expectation from the code under
# test would pass no matter how that code changed. Every one of the 6 sources
# (``None`` plus the five states) is crossed with every one of the 5 targets, so
# there is no pair this table leaves unsaid.
#
# This is the *legality* contract, not the *offering* contract: which of these
# moves a given user is invited to make is decided separately, by permissions.
# Changing a cell here changes what the database will accept. Do not edit it to
# make another test pass.
LEGALITY_MATRIX = {
    #  from            ORDERED  INROOM   LENT    LOST   REMOVED
    None: {"ORDERED": True, "INROOM": True, "LENT": False, "LOST": False, "REMOVED": True},
    "ORDERED": {"ORDERED": False, "INROOM": True, "LENT": False, "LOST": False, "REMOVED": True},
    "INROOM": {"ORDERED": False, "INROOM": True, "LENT": True, "LOST": True, "REMOVED": True},
    "LENT": {"ORDERED": False, "INROOM": True, "LENT": False, "LOST": True, "REMOVED": True},
    "LOST": {"ORDERED": False, "INROOM": True, "LENT": False, "LOST": True, "REMOVED": True},
    "REMOVED": {"ORDERED": False, "INROOM": True, "LENT": False, "LOST": True, "REMOVED": False},
}


@pytest.mark.parametrize(
    "frm, to, allowed",
    [(frm, to, allowed) for frm, row in LEGALITY_MATRIX.items() for to, allowed in row.items()],
)
def test_can_transition_matrix(frm, to, allowed):
    assert lifecycle.can_transition(frm, to) is allowed


def test_legality_matrix_covers_every_state_pair():
    """The matrix above is exhaustive -- if a state is ever added, this fails
    until the new row and column are filled in."""
    assert set(LEGALITY_MATRIX) == {None, *lifecycle.RECORD_TYPE_KEYS}
    for row in LEGALITY_MATRIX.values():
        assert set(row) == set(lifecycle.RECORD_TYPE_KEYS)


# --- Offering is permissions, and nothing else ---------------------------
# Whether a legal move is surfaced used to be hardcoded here as ``offered`` /
# ``not_offered_from`` flags. It is now entirely a question of who holds the
# transition's permission, so what these tests pin is the declaration itself --
# that every row names a permission, and that the permissions it names are ones
# the project actually creates. A typo'd permission string fails closed: the
# button silently disappears for everyone, which no other test would catch.


def test_every_transition_declares_a_permission():
    for t in lifecycle.TRANSITIONS:
        assert t.permission, f"transition {t.name!r} has no permission"
        assert t.permission.startswith("core."), f"transition {t.name!r} has an unscoped permission"


def test_permission_for_returns_the_declared_permission():
    for t in lifecycle.TRANSITIONS:
        assert lifecycle.permission_for(t) == t.permission


def test_lending_and_returning_share_one_permission():
    """Handing a device out and taking it back are one competence."""
    assert lifecycle.BY_NAME["lend"].permission == lifecycle.BY_NAME["return_lending"].permission


def test_the_ways_out_of_removed_have_permissions_of_their_own():
    """The point of the whole exercise.

    ``restore`` and ``recover`` write a LostRecord and an InRoomRecord, so under
    the old ``add_<target proxy>`` derivation they were indistinguishable from
    ``lose`` and ``relocate`` -- anyone who could move a device could un-remove
    one. Nothing else may share their permissions.
    """
    exclusive = {lifecycle.BY_NAME["restore"].permission, lifecycle.BY_NAME["recover"].permission}
    others = {t.permission for t in lifecycle.TRANSITIONS if t.name not in {"restore", "recover"}}
    assert not exclusive & others


def test_transition_permissions_are_declared_on_the_record_model():
    """Every permission the table names is one ``Record.Meta`` actually creates."""
    declared = {f"core.{codename}" for codename, _ in Record._meta.permissions}
    referenced = {t.permission for t in lifecycle.TRANSITIONS}
    assert referenced <= declared, f"undeclared: {sorted(referenced - declared)}"


@pytest.mark.django_db
def test_transition_permissions_exist_in_the_database():
    """The declaration is not enough -- the rows must be there to be granted."""
    from django.contrib.auth.models import Permission

    for t in lifecycle.TRANSITIONS:
        codename = t.permission.removeprefix("core.")
        assert Permission.objects.filter(codename=codename, content_type__app_label="core").exists(), (
            f"transition {t.name!r} names {t.permission!r}, which no Permission row provides"
        )


# --- Enforcement ---------------------------------------------------------


@pytest.mark.django_db
def test_a_lentable_licence_is_lendable(room):
    """Lendability is decided by is_lentable alone -- a licence flagged lentable
    is offered for lending like any other device."""
    from dlcdb.core.models import Device

    licence = Device.objects.create(edv_id="LIC-LEND", is_lentable=True, is_licence=True)
    InRoomRecord.objects.create(device=licence, room=room)

    assert licence.pk in lifecycle.devices_for("lend").values_list("pk", flat=True)


@pytest.mark.django_db
def test_a_non_lentable_device_is_not_lendable(room):
    from dlcdb.core.models import Device

    device = Device.objects.create(edv_id="NOLEND", is_lentable=False)
    InRoomRecord.objects.create(device=device, room=room)

    assert device.pk not in lifecycle.devices_for("lend").values_list("pk", flat=True)


@pytest.mark.django_db
def test_a_lent_licence_is_visible_to_the_lending_manager(room):
    """The flip side of lending licences: once lent, the lending must show up in
    ``LentRecord.objects`` -- the queryset behind the lending frontend, the API,
    the admin changelist and the dashboard. Lending a device its own list views
    cannot see again would strand it."""
    from dlcdb.core.models import Device

    licence = Device.objects.create(edv_id="LIC-LENT", is_lentable=True, is_licence=True)
    InRoomRecord.objects.create(device=licence, room=room)
    licence.refresh_from_db()

    record = lifecycle.transition_lend(
        licence,
        person=None,
        room=room,
        lent_start_date="2026-01-01",
        lent_desired_end_date="2099-01-01",
        user=None,
    )

    assert record.pk in LentRecord.objects.values_list("pk", flat=True)


@pytest.mark.django_db
def test_lending_a_non_lentable_device_is_rejected(room):
    """``device_precondition`` is enforced by the transition itself, not only
    when offering UI actions."""
    from dlcdb.core.models import Device

    device = Device.objects.create(edv_id="NOLEND-WRITE", is_lentable=False)
    InRoomRecord.objects.create(device=device, room=room)
    device.refresh_from_db()

    with pytest.raises(lifecycle.IllegalTransition):
        lifecycle.transition_lend(
            device,
            person=None,
            room=room,
            lent_start_date="2026-01-01",
            lent_desired_end_date="2099-01-01",
            user=None,
        )


@pytest.mark.django_db
def test_relocate_lending_rejects_a_non_lending_record(lentable_device, room):
    """The in-place move is only for the active LENT record; handing it any
    other record must not silently edit history."""
    record = InRoomRecord.objects.create(device=lentable_device, room=room)

    with pytest.raises(lifecycle.IllegalTransition):
        lifecycle.relocate_lending(record, room=room, user=None)


@pytest.mark.django_db
def test_illegal_insert_is_rejected(plain_device, room):
    """A device with no record cannot jump straight to LENT."""
    with pytest.raises(lifecycle.IllegalTransition):
        LentRecord.objects.create(device=plain_device, room=room)


@pytest.mark.django_db
def test_check_transition_false_bypasses_enforcement(plain_device, room):
    record = LentRecord(device=plain_device, room=room)
    record.save(check_transition=False)  # must not raise
    plain_device.refresh_from_db()
    assert plain_device.active_record.record_type == Record.LENT


@pytest.mark.django_db
def test_legal_transition_via_function(lentable_device, room):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()

    lifecycle.transition_lose(lentable_device, user=None)

    lentable_device.refresh_from_db()
    assert lentable_device.active_record.record_type == Record.LOST


@pytest.mark.django_db
def test_transition_function_rejects_illegal_source(plain_device):
    """The front door is stricter: transition_find only accepts a LOST device."""
    room = Room.objects.create(number="LC-1")
    with pytest.raises(lifecycle.IllegalTransition):
        lifecycle.transition_find(plain_device, room=room, user=None)


@pytest.mark.django_db
def test_return_lending_is_atomic(lentable_device, room):
    """
    A return that cannot find the auto-return room leaves no partial change:
    the lending is not stamped with an end date.
    """
    InRoomRecord.objects.create(device=lentable_device, room=room)
    lentable_device.refresh_from_db()
    record = lifecycle.transition_lend(
        lentable_device,
        person=None,
        room=room,
        lent_start_date="2026-01-01",
        lent_desired_end_date="2099-01-01",
        user=None,
    )
    # No Room is flagged is_auto_return_room, so the return must fail...
    with pytest.raises(Room.DoesNotExist):
        lifecycle.transition_return_lending(record, user=None, lent_end_date="2026-02-01")

    # ...and roll back cleanly: the lending is still open.
    record.refresh_from_db()
    assert record.lent_end_date is None
