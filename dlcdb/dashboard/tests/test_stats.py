# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Month counting behind the dashboard's record timeline."""

import datetime

from dlcdb.core.models import Record
from dlcdb.dashboard.stats import devices_per_month

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
