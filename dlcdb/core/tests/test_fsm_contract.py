# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for the device lifecycle state machine contract.

These pin down the pieces that currently live in ``dlcdb/core/models/record.py``
-- the ``STATE_TRANSITIONS`` table, the record-type -> proxy registry and the
colour map -- so that consolidating them into a central FSM cannot silently
change behaviour.

Transition legality is asserted as *subset* checks on purpose. The table is known
to be incomplete: production code performs REMOVED -> LOST
(``device_admin.restore_removed_to_lost``) and REMOVED -> INROOM
(``Inventory.inventorize_uuids_for_room``), and ORDERED is a dead end although
``procure_forms`` still creates ORDERED records. Correcting the table must not
break these tests.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from dlcdb.core import lifecycle
from dlcdb.core.models import Record
from dlcdb.core.models.record import RECORD_TYPE_COLORS, RECORD_TYPE_KEYS, RECORD_TYPE_LIST


def _unsaved(record_type):
    """A throwaway instance just to query the state machine helpers."""
    return Record(record_type=record_type)


# --- The public contract -------------------------------------------------


def test_record_type_keys_are_the_public_contract():
    """
    These exact strings are baked into the DB CheckConstraint
    (``core/migrations/0060_*``) and into the read-only API (raw ``record_type``
    values plus the ``active_record__record_type`` filter). A refactoring may
    reorganise transitions freely but must not rename or drop a state -- hence
    exact equality here, unlike the transition assertions below.
    """
    assert set(RECORD_TYPE_KEYS) == {"ORDERED", "INROOM", "LENT", "LOST", "REMOVED"}


def test_record_type_constants_match_the_choice_list():
    """The ``Record.<STATE>`` class attributes and RECORD_TYPE_LIST cannot drift."""
    for key in RECORD_TYPE_KEYS:
        assert getattr(Record, key) == key
    assert [choice[0] for choice in RECORD_TYPE_LIST] == RECORD_TYPE_KEYS


# --- Table shape ---------------------------------------------------------


def _targets(state):
    """The set of target states reachable from ``state`` per the lifecycle table."""
    return {t.target for t in lifecycle.transitions_from(state)}


@pytest.mark.parametrize(
    "state, expected_targets",
    [
        (None, {Record.INROOM}),
        (Record.INROOM, {Record.INROOM, Record.LENT, Record.LOST, Record.REMOVED}),
        (Record.LENT, {Record.INROOM, Record.LOST}),
        (Record.LOST, {Record.INROOM, Record.REMOVED}),
    ],
)
def test_known_transitions_are_allowed(state, expected_targets):
    """
    Subset, not equality: the corrected table legitimately has extra targets
    (e.g. LENT -> LOST, REMOVED -> LOST/INROOM).
    """
    assert expected_targets <= _targets(state)


def test_inroom_is_reachable_from_every_operational_state():
    """
    INROOM is the hub of the machine -- a device can always be brought back to
    "located in a room" from any state a live device can be in (including REMOVED,
    via the inventory ``recover`` transition).
    """
    for state in (None, Record.INROOM, Record.LENT, Record.LOST, Record.REMOVED):
        assert Record.INROOM in _targets(state)


def test_can_transition_agrees_with_the_table():
    for state in (None, Record.INROOM, Record.LENT, Record.LOST, Record.REMOVED):
        for target in _targets(state):
            assert lifecycle.can_transition(state, target)


def test_ordered_can_be_located_or_removed():
    """
    ORDERED used to be a dead end (commented out of the old STATE_TRANSITIONS).
    The corrected table gives it a way forward: an ordered device is located when
    it arrives, or removed if the order is cancelled.
    """
    assert _targets(Record.ORDERED) == {Record.INROOM, Record.REMOVED}


def test_unknown_state_yields_no_transitions_instead_of_raising():
    assert lifecycle.transitions_from("NO_SUCH_STATE") == ()


# --- Registry completeness ----------------------------------------------


def test_every_record_type_resolves_to_a_proxy_model():
    """
    Catches the "added a record type and forgot one of the four places" bug:
    RECORD_TYPE_LIST, the proxy registry, RECORD_TYPE_COLORS and the proxy model
    itself all have to agree.
    """
    for key in RECORD_TYPE_KEYS:
        proxy = Record.get_proxy_model_by_record_type(key)
        assert proxy._meta.proxy, f"{proxy.__name__} must be a proxy model"
        assert issubclass(proxy, Record)


@pytest.mark.django_db
def test_every_proxy_stamps_its_own_record_type(plain_device):
    """
    Each proxy's ``save()`` force-sets ``record_type``, which is what makes the
    proxy the de-facto transition primitive today.
    """
    for key in RECORD_TYPE_KEYS:
        proxy = Record.get_proxy_model_by_record_type(key)
        # Deliberately pass a wrong record_type: save() must overwrite it.
        instance = proxy(device=plain_device, record_type="WRONG")
        instance.save()
        assert instance.record_type == key
        assert Record.objects.get(pk=instance.pk).record_type == key


@pytest.mark.django_db
def test_get_proxy_instance_returns_the_concrete_proxy(plain_device, room):
    from dlcdb.core.models import InRoomRecord

    record = InRoomRecord.objects.create(device=plain_device, room=room)
    base = Record.objects.get(pk=record.pk)
    assert type(base) is Record
    assert type(base.get_proxy_instance()) is InRoomRecord


# --- Presentation metadata ----------------------------------------------


def test_colour_map_covers_every_record_type():
    assert set(RECORD_TYPE_COLORS) == set(RECORD_TYPE_KEYS)


@pytest.mark.parametrize("key", RECORD_TYPE_KEYS)
def test_record_type_color_matches_the_map(key):
    assert _unsaved(key).record_type_color == RECORD_TYPE_COLORS[key]


def test_record_type_color_falls_back_for_unknown_states():
    assert _unsaved("NO_SUCH_STATE").record_type_color == "secondary"


# --- Guards --------------------------------------------------------------


@pytest.mark.django_db
def test_check_constraint_rejects_an_empty_record_type(plain_device):
    # Bypass the lifecycle check so the DB CheckConstraint (defense in depth) is
    # what rejects the row, not the transition guard.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Record(device=plain_device, record_type="").save(check_transition=False)


@pytest.mark.django_db
def test_check_constraint_rejects_an_unknown_record_type(plain_device):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Record(device=plain_device, record_type="NO_SUCH_STATE").save(check_transition=False)


@pytest.mark.django_db
def test_plain_records_are_rejected_by_clean(plain_device):
    plain = Record(device=plain_device, record_type=Record.ORDERED)
    assert not plain._meta.proxy
    with pytest.raises(ValidationError):
        plain.clean()


@pytest.mark.django_db
def test_plain_records_bypass_the_proxy_guard_on_save(plain_device):
    """
    Current behaviour, and a finding worth pinning: ``Record.clean()`` forbids
    non-proxy records, but neither ``save()`` nor ``objects.create()`` calls
    ``clean()``. Two production paths rely on this hole --
    ``core/admin/record_admin.py`` and ``dataexchange/remover.py`` both write
    plain ``Record`` rows.

    A future FSM is expected to close this. When it does, this test should be
    updated to assert the rejection rather than deleted.
    """
    record = Record.objects.create(device=plain_device, record_type=Record.REMOVED)
    assert record.pk is not None
    plain_device.refresh_from_db()
    assert plain_device.active_record.pk == record.pk
