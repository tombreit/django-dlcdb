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


@pytest.mark.parametrize(
    "frm, to, allowed",
    [
        (None, lifecycle.INROOM, True),  # locate
        (None, lifecycle.LENT, False),  # cannot lend a device with no record
        (lifecycle.INROOM, lifecycle.LENT, True),  # lend
        (lifecycle.LENT, lifecycle.INROOM, True),  # return
        (lifecycle.LENT, lifecycle.REMOVED, True),  # decommission while lent (admin)
        (lifecycle.REMOVED, lifecycle.INROOM, True),  # recover (inventory)
        (lifecycle.REMOVED, lifecycle.LENT, False),  # cannot lend a removed device
        (lifecycle.LOST, lifecycle.LENT, False),  # cannot lend a lost device
    ],
)
def test_can_transition_matrix(frm, to, allowed):
    assert lifecycle.can_transition(frm, to) is allowed


# --- Offering vs legality -----------------------------------------------


def test_remove_is_legal_from_lent_but_not_offered_there():
    assert lifecycle.can_transition(lifecycle.LENT, lifecycle.REMOVED)
    offered_targets = {t.target for t in lifecycle.offered_transitions_from(lifecycle.LENT)}
    assert lifecycle.REMOVED not in offered_targets


def test_removed_offers_nothing():
    assert lifecycle.offered_transitions_from(lifecycle.REMOVED) == ()


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
