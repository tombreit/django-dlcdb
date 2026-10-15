# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Counting behind the dashboard's record charts: the months of the timeline, the states of the record chart."""

import datetime

import pytest

from dlcdb.core.models import Device, DeviceType, InRoomRecord, LentRecord, LostRecord, Record, Room
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.dashboard.stats import (
    DEVICE_TYPE_MIN_COUNT,
    active_record_counts,
    devices_per_month,
    get_device_type_html,
)

NOW = datetime.datetime(2026, 10, 15, 12, tzinfo=datetime.UTC)


def _at(year, month, day=10):
    return datetime.datetime(year, month, day, 12, tzinfo=datetime.UTC)


def _months(records, record_type):
    return sorted(devices_per_month(records, now=NOW)[record_type])


def test_a_record_owns_its_months_up_to_the_one_it_was_superseded_in():
    records = [(1, Record.INROOM, _at(2026, 3), _at(2026, 6))]

    assert _months(records, Record.INROOM) == ["2026-03", "2026-04", "2026-05"]


def test_an_active_record_counts_through_the_current_month():
    records = [(1, Record.LENT, _at(2026, 8), None)]

    assert _months(records, Record.LENT) == ["2026-08", "2026-09", "2026-10"]


def test_a_record_superseded_within_its_own_month_owns_no_month():
    records = [(1, Record.LOST, _at(2026, 3, 5), _at(2026, 3, 20))]

    assert _months(records, Record.LOST) == []


def test_months_run_across_the_turn_of_the_year():
    records = [(1, Record.INROOM, _at(2025, 11), _at(2026, 2))]

    assert _months(records, Record.INROOM) == ["2025-11", "2025-12", "2026-01"]


def test_a_removal_counts_only_in_its_own_month():
    records = [(1, Record.REMOVED, _at(2025, 4), None)]

    assert _months(records, Record.REMOVED) == ["2025-04"]


def test_a_device_counts_once_per_month():
    """Two records of one device in the same month: one device, not two."""
    records = [
        (1, Record.INROOM, _at(2026, 3, 1), _at(2026, 4, 2)),
        (1, Record.INROOM, _at(2026, 4, 2), _at(2026, 4, 3)),
        (1, Record.INROOM, _at(2026, 4, 3), None),
        (2, Record.INROOM, _at(2026, 3, 1), None),
    ]

    counts = devices_per_month(records, now=_at(2026, 4))[Record.INROOM]
    assert {month: sorted(devices) for month, devices in counts.items()} == {"2026-03": [1, 2], "2026-04": [1, 2]}


@pytest.mark.django_db
def test_the_record_chart_counts_each_device_once_by_its_state(tenant):
    """A lentable device is lent only while its active record is LENT, not while available or lost."""
    room = Room.objects.create(number="A1.23")

    def lentable(edv_id, proxy_model, **fields):
        device = Device.objects.create(edv_id=edv_id, is_lentable=True, tenant=tenant)
        establish_state(proxy_model, device=device, **fields)

    lentable("EDV-AVAILABLE", InRoomRecord, room=room)
    lentable(
        "EDV-LENT",
        LentRecord,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2026, 12, 31),
    )
    lentable("EDV-LOST", LostRecord)

    assert active_record_counts(tenants=[tenant]) == {"inroom": 1, "lent": 1, "lost": 1, "removed": 0}


@pytest.mark.django_db
def test_the_device_type_chart_shows_only_types_with_enough_devices(tenant):
    """Below the minimum there is no chart at all, so the template shows its note instead."""
    beamer = DeviceType.objects.create(name="Beamer", prefix="BMR")
    for number in range(DEVICE_TYPE_MIN_COUNT - 1):
        Device.objects.create(edv_id=f"BMR-{number}", device_type=beamer, tenant=tenant)

    assert get_device_type_html(tenants=[tenant]) == ""

    Device.objects.create(edv_id="BMR-LAST", device_type=beamer, tenant=tenant)

    assert "Beamer" in get_device_type_html(tenants=[tenant])
