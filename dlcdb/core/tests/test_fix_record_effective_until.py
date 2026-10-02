# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The ``fix_record_modified_at_timestamps`` command rewrites history: what it
repairs, and everything it must leave alone.
"""

import dataclasses
import datetime
from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command

from dlcdb.core.management.commands.fix_record_modified_at_timestamps import apply_repairs, find_repairs
from dlcdb.core.models import InRoomRecord, Record
from dlcdb.core.tests.testingutils import establish_state

pytestmark = pytest.mark.django_db

T0 = datetime.datetime(2020, 1, 1, 12, tzinfo=datetime.UTC)
DAY = datetime.timedelta(days=1)
# Record.save() closes the superseded record just before its successor is written.
STAMP_LEAD = datetime.timedelta(milliseconds=5)
# The latest append, which the old Record.save() stamped onto every earlier record.
BULK_STAMP = datetime.datetime(2025, 8, 12, 9, tzinfo=datetime.UTC)


def _set_correct_times(pks, start=T0):
    """One day apart, each record closed a few milliseconds before its successor was created."""
    for index, pk in enumerate(pks):
        created = start + index * DAY
        closed = created + DAY - STAMP_LEAD if index < len(pks) - 1 else None
        Record.objects.filter(pk=pk).update(created_at=created, effective_until=closed)


def _chain(device, room, length, start=T0):
    """``length`` records of ``device`` with correct timestamps; returns their pks, oldest first."""
    pks = [establish_state(InRoomRecord, device=device, room=room).pk for _ in range(length)]
    _set_correct_times(pks, start)
    return pks


def _over_stamp(pks):
    """What Record.save() did before 92e230c: stamp every earlier record with the latest append."""
    Record.objects.filter(pk__in=pks[:-1]).update(effective_until=BULK_STAMP)


def _effective_until(pks):
    return [Record.objects.get(pk=pk).effective_until for pk in pks]


def _created(pks):
    return [Record.objects.get(pk=pk).created_at for pk in pks]


def _closed_by_successors(pks):
    """The repaired chain: each record valid until its successor was created, the latest still open."""
    return [*_created(pks)[1:], None]


def _run(*args):
    out = StringIO()
    call_command("fix_record_modified_at_timestamps", *args, stdout=out)
    return out.getvalue()


def test_dry_run_is_the_default_and_writes_nothing(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)

    output = _run("--repair-overstamped")

    assert _effective_until(pks) == [BULK_STAMP, BULK_STAMP, None]
    assert "nothing written: 2 record(s) would change" in output


def test_repair_overstamped_closes_each_record_at_its_successors_creation(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)

    _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks) == _closed_by_successors(pks)


def test_without_repair_overstamped_only_empty_values_are_filled(device_1, room):
    pks = _chain(device_1, room, 4)
    _over_stamp(pks)
    Record.objects.filter(pk=pks[1]).update(effective_until=None)

    output = _run("--mode", "write")

    assert _effective_until(pks) == [BULK_STAMP, _created(pks)[2], BULK_STAMP, None]
    assert "Add --repair-overstamped to repair them." in output


def test_correct_values_are_left_exactly_as_they_are(device_1, room):
    """A correct stamp precedes its successor by milliseconds; it must not be "normalised"."""
    pks = _chain(device_1, room, 3)
    before = _effective_until(pks)

    _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks) == before


def test_values_backfilled_by_the_original_run_are_left_alone(device_1, room):
    """The 2022 backfill wrote exactly the successor's creation: correct, and no repair."""
    pks = _chain(device_1, room, 3)
    for pk, successor_created in zip(pks, _created(pks)[1:]):
        Record.objects.filter(pk=pk).update(effective_until=successor_created)
    before = _effective_until(pks)

    output = _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks) == before
    assert "0 empty value(s), 0 over-stamped value(s)" in output


def test_the_active_record_is_never_touched(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    # An anomaly: the active record claims an end of validity. Still not ours to change.
    Record.objects.filter(pk=pks[-1]).update(effective_until=BULK_STAMP)

    _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks)[-1] == BULK_STAMP


def test_successors_come_from_the_same_device(device_1, device_2, room):
    """Interleaved record ids: the next record by id belongs to the other device."""
    pks_1, pks_2 = [], []
    for _ in range(3):
        pks_1.append(establish_state(InRoomRecord, device=device_1, room=room).pk)
        pks_2.append(establish_state(InRoomRecord, device=device_2, room=room).pk)
    _set_correct_times(pks_1, start=T0)
    _set_correct_times(pks_2, start=T0 + datetime.timedelta(hours=6))
    _over_stamp(pks_1)
    _over_stamp(pks_2)

    _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks_1) == _closed_by_successors(pks_1)
    assert _effective_until(pks_2) == _closed_by_successors(pks_2)


def test_a_chain_with_creation_times_out_of_order_is_skipped(device_1, device_2, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    # The first record created after the second: which one superseded which is no longer clear.
    Record.objects.filter(pk=pks[0]).update(created_at=T0 + 10 * DAY)
    healthy = _chain(device_2, room, 3)
    _over_stamp(healthy)

    output = _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks) == [BULK_STAMP, BULK_STAMP, None]
    assert f"skipped device {device_1.pk}: creation times are out of record order" in output
    assert _effective_until(healthy) == _closed_by_successors(healthy), "other devices are still repaired"


@pytest.mark.parametrize(
    "active_flags",
    [
        pytest.param((True, False, True), id="two-active-records"),
        pytest.param((True, False, False), id="active-record-not-the-latest"),
        pytest.param((False, False, False), id="no-active-record"),
    ],
)
def test_a_chain_without_exactly_one_active_latest_record_is_skipped(device_1, room, active_flags):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    for pk, is_active in zip(pks, active_flags, strict=True):
        Record.objects.filter(pk=pk).update(is_active=is_active)

    output = _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks) == [BULK_STAMP, BULK_STAMP, None]
    assert f"skipped device {device_1.pk}: the latest record is not the only active one" in output


def test_only_effective_until_changes(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    Record.objects.filter(pk__in=pks).update(modified_at=T0 - DAY)

    def snapshot():
        rows = list(Record.objects.filter(pk__in=pks).order_by("pk").values())
        for row in rows:
            del row["effective_until"]
        return rows

    before = snapshot()
    _run("--repair-overstamped", "--mode", "write")

    assert snapshot() == before


def test_a_second_run_finds_nothing(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    _run("--repair-overstamped", "--mode", "write")

    assert find_repairs() == ([], [])
    assert "0 empty value(s), 0 over-stamped value(s)" in _run("--repair-overstamped")


def test_device_option_limits_report_and_write(device_1, device_2, room):
    pks_1 = _chain(device_1, room, 3)
    pks_2 = _chain(device_2, room, 3)
    _over_stamp(pks_1)
    _over_stamp(pks_2)

    output = _run("--repair-overstamped", "--mode", "write", "--device", str(device_1.pk))

    assert "2 record(s) written" in output
    assert _effective_until(pks_1) == _closed_by_successors(pks_1)
    assert _effective_until(pks_2) == [BULK_STAMP, BULK_STAMP, None]


def test_an_unknown_device_is_an_error_not_a_silent_no_op():
    with pytest.raises(CommandError, match="has no records"):
        _run("--device", "999999")


def test_a_record_changed_since_the_scan_is_left_alone(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    repairs, _skipped = find_repairs()
    changed_meanwhile = T0 + datetime.timedelta(hours=1)
    Record.objects.filter(pk=pks[0]).update(effective_until=changed_meanwhile)

    written = apply_repairs(repairs)

    assert written == 1
    assert _effective_until(pks) == [changed_meanwhile, _created(pks)[2], None]


def test_a_failing_write_rolls_back_the_whole_run(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    repairs, _skipped = find_repairs()
    broken = dataclasses.replace(repairs[1], new="not a timestamp")

    with pytest.raises(ValidationError):
        apply_repairs([repairs[0], broken])

    assert _effective_until(pks) == [BULK_STAMP, BULK_STAMP, None], "the first repair must not stick"


def test_records_of_soft_deleted_devices_are_repaired_too(device_1, room):
    pks = _chain(device_1, room, 3)
    _over_stamp(pks)
    device_1.delete()

    _run("--repair-overstamped", "--mode", "write")

    assert _effective_until(pks) == _closed_by_successors(pks)
