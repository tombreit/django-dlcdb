# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
What makes a lending overdue (``LentRecord.overdue_q``, ``LentRecord.objects.overdue()``):
a LENT record, not returned yet, whose desired return date plus the tolerance is on or
before today.
"""

import datetime
import itertools
from datetime import timedelta
from unittest import mock

import pytest

from dlcdb.core.models import Device, InRoomRecord, LentRecord, Room
from dlcdb.core.tests.testingutils import establish_state

TODAY = datetime.date(2026, 6, 15)


@pytest.fixture
def lend(tenant):
    """A lentable device in the given state, with the given lending fields."""
    room = Room.objects.create(number="A1.23")
    numbers = itertools.count(1)

    def _lend(proxy_model=LentRecord, **fields):
        device = Device.objects.create(edv_id=f"EDV-{next(numbers)}", is_lentable=True, tenant=tenant)
        return establish_state(
            proxy_model, device=device, room=room, lent_start_date=datetime.date(2026, 1, 1), **fields
        )

    return _lend


def _overdue(**kwargs):
    return set(LentRecord.objects.overdue(today=TODAY, **kwargs))


@pytest.mark.django_db
def test_due_on_or_before_the_day_and_not_returned_is_overdue(lend):
    due_yesterday = lend(lent_desired_end_date=TODAY - timedelta(days=1))
    due_today = lend(lent_desired_end_date=TODAY)
    lend(lent_desired_end_date=TODAY + timedelta(days=1))
    lend(lent_desired_end_date=TODAY - timedelta(days=1), lent_end_date=TODAY - timedelta(days=1))

    assert _overdue() == {due_yesterday, due_today}


@pytest.mark.django_db
def test_only_a_lent_record_can_be_overdue(lend):
    """LentRecord.objects also holds the INROOM records of lentable devices."""
    lend(InRoomRecord, lent_desired_end_date=TODAY - timedelta(days=1))

    assert _overdue() == set()


@pytest.mark.django_db
def test_the_tolerance_postpones_overdue(lend):
    five_days_late = lend(lent_desired_end_date=TODAY - timedelta(days=5))
    lend(lent_desired_end_date=TODAY - timedelta(days=4))

    assert _overdue(tolerance_days=5) == {five_days_late}


@pytest.mark.django_db
def test_the_last_date_python_knows_does_not_overflow(lend):
    lend(lent_desired_end_date=datetime.date.max)

    assert _overdue(tolerance_days=5) == set()


@pytest.mark.django_db
def test_the_default_day_is_today_in_local_time(lend):
    due_today = lend(lent_desired_end_date=TODAY)
    # 22:30 UTC on the day before is already TODAY in Berlin (TIME_ZONE, summer time).
    late_evening_utc = datetime.datetime(2026, 6, 14, 22, 30, tzinfo=datetime.UTC)

    with mock.patch("django.utils.timezone.now", return_value=late_evening_utc):
        assert set(LentRecord.objects.overdue()) == {due_today}
