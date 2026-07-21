# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for the append-only record chain.

"Records are append-only, the newest one is active" is the central promise of the
data model (see ``docs/konzept.md``). Every state change is supposed to *append* a
record rather than modify one. These tests pin that invariant down before the
transition logic is consolidated into a central FSM.

Assertions are deliberately about *outcomes* (which record is active, what the
device points at) rather than mechanisms, so they survive a refactoring that
changes how a transition is performed.
"""

import datetime

import pytest
from django.utils import timezone

from dlcdb.core.models import Device, InRoomRecord, LentRecord, LostRecord, Record, RemovedRecord


@pytest.mark.django_db
def test_appending_deactivates_the_previous_record(lentable_device, room):
    first = InRoomRecord.objects.create(device=lentable_device, room=room)
    assert Record.objects.get(pk=first.pk).is_active

    second = LostRecord.objects.create(device=lentable_device)

    assert not Record.objects.get(pk=first.pk).is_active
    assert Record.objects.get(pk=second.pk).is_active


@pytest.mark.django_db
def test_exactly_one_record_is_active_along_a_chain(lentable_device, room):
    """Walk a realistic lifecycle, checking the invariant after every step."""
    steps = [
        lambda: InRoomRecord.objects.create(device=lentable_device, room=room),
        lambda: LentRecord.objects.create(device=lentable_device, room=room),
        lambda: InRoomRecord.objects.create(device=lentable_device, room=room),
        lambda: LostRecord.objects.create(device=lentable_device),
        lambda: RemovedRecord.objects.create(device=lentable_device),
    ]

    for step, make_record in enumerate(steps, start=1):
        record = make_record()

        active = Record.objects.filter(device=lentable_device, is_active=True)
        assert active.count() == 1, f"expected exactly one active record after step {step}"
        assert active.get().pk == record.pk, f"the newest record must be active after step {step}"

        lentable_device.refresh_from_db()
        assert lentable_device.active_record.pk == record.pk

    assert Record.objects.filter(device=lentable_device).count() == len(steps)


@pytest.mark.django_db
def test_device_active_record_matches_the_active_row(lentable_device, room):
    """
    ``Device.active_record`` is a denormalised cache of "the record with
    is_active=True". The two must never disagree.
    """
    InRoomRecord.objects.create(device=lentable_device, room=room)
    latest = LentRecord.objects.create(device=lentable_device, room=room)

    lentable_device.refresh_from_db()
    active_row = Record.objects.get(device=lentable_device, is_active=True)
    assert lentable_device.active_record.pk == active_row.pk == latest.pk


@pytest.mark.django_db
def test_appending_closes_the_previous_record(lentable_device, room):
    """A superseded record gets an ``effective_until`` timestamp."""
    first = InRoomRecord.objects.create(device=lentable_device, room=room)
    assert first.effective_until is None

    before = timezone.now()
    LostRecord.objects.create(device=lentable_device)
    after = timezone.now()

    first.refresh_from_db()
    assert first.effective_until is not None
    assert before <= first.effective_until <= after


@pytest.mark.django_db
def test_the_active_record_is_open_ended(lentable_device, room):
    InRoomRecord.objects.create(device=lentable_device, room=room)
    latest = LostRecord.objects.create(device=lentable_device)

    latest.refresh_from_db()
    assert latest.is_active
    assert latest.effective_until is None


@pytest.mark.django_db
def test_appending_does_not_touch_other_devices(room):
    """``Record.save()`` scopes its deactivation to ``self.device``."""
    device_a = Device.objects.create(edv_id="EDV-A")
    device_b = Device.objects.create(edv_id="EDV-B")

    record_a = InRoomRecord.objects.create(device=device_a, room=room)
    InRoomRecord.objects.create(device=device_b, room=room)
    LostRecord.objects.create(device=device_b)

    record_a.refresh_from_db()
    assert record_a.is_active
    assert record_a.effective_until is None
    device_a.refresh_from_db()
    assert device_a.active_record.pk == record_a.pk


@pytest.mark.django_db
def test_editing_a_record_does_not_append(lentable_device, room):
    """
    Editing an existing record (changing a note, a lending's dates, ...) is not
    a transition: it must not create a record, flip activity or close anything.
    The distinction is ``_state.adding`` in ``Record.save()``.
    """
    record = LentRecord.objects.create(
        device=lentable_device,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )
    count_before = Record.objects.filter(device=lentable_device).count()

    record.lent_note = "Charger included"
    record.save()

    assert Record.objects.filter(device=lentable_device).count() == count_before
    record.refresh_from_db()
    assert record.is_active
    assert record.effective_until is None
    assert record.lent_note == "Charger included"
    lentable_device.refresh_from_db()
    assert lentable_device.active_record.pk == record.pk


@pytest.mark.django_db
def test_history_is_preserved_not_overwritten(lentable_device, room):
    """The whole point of the chain: superseded records stay readable."""
    inroom = InRoomRecord.objects.create(device=lentable_device, room=room)
    LostRecord.objects.create(device=lentable_device)

    inroom.refresh_from_db()
    assert inroom.record_type == Record.INROOM
    assert inroom.room == room
    assert Record.objects.filter(device=lentable_device).count() == 2


# --- Proxy field side effects -------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("proxy", [LostRecord, RemovedRecord])
def test_lost_and_removed_records_have_no_room(lentable_device, room, proxy):
    record = proxy.objects.create(device=lentable_device, room=room)
    assert record.room is None
    assert Record.objects.get(pk=record.pk).room is None


@pytest.mark.django_db
def test_removed_record_stamps_a_removal_date(lentable_device):
    record = RemovedRecord.objects.create(device=lentable_device)
    assert record.removed_date is not None


@pytest.mark.django_db
def test_removed_record_preserves_a_given_removal_date(lentable_device):
    stamped = timezone.make_aware(datetime.datetime(2020, 5, 4, 12, 0))
    record = RemovedRecord.objects.create(device=lentable_device, removed_date=stamped)
    assert record.removed_date == stamped


@pytest.mark.django_db
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Known defect: Record.save() stamps effective_until on ALL previous "
        "records of the device, not just the one being superseded, so a record's "
        "close timestamp is rewritten every time the device changes state again. "
        "dashboard/stats.py documents this in a comment and works around it. "
        "Kept as xfail so it flips to green once a consolidated FSM closes only "
        "the record it supersedes."
    ),
)
def test_closing_timestamp_reflects_when_a_record_actually_ended(lentable_device, room):
    first = InRoomRecord.objects.create(device=lentable_device, room=room)
    LostRecord.objects.create(device=lentable_device)

    first.refresh_from_db()
    closed_at = first.effective_until

    # A later, unrelated state change must not move the first record's end date.
    InRoomRecord.objects.create(device=lentable_device, room=room)

    first.refresh_from_db()
    assert first.effective_until == closed_at
