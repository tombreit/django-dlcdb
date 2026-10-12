# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The ``license_state`` annotation of the ``LicenceRecord`` manager around the
``EXPIRING_WITHIN_DAYS`` window, and the records the manager lists at all.
"""

import datetime
from unittest import mock

import pytest

from dlcdb.core.models import Device, InRoomRecord, LicenceRecord, RemovedRecord, Room
from dlcdb.core.models.prx_licencerecord import EXPIRING_WITHIN_DAYS

TODAY = datetime.date(2026, 10, 12)


@pytest.fixture(autouse=True)
def fixed_today():
    noon = datetime.datetime(2026, 10, 12, 10, 0, tzinfo=datetime.UTC)  # 12:00 CEST
    with mock.patch("django.utils.timezone.now", return_value=noon):
        yield


def _licence(expires_in_days):
    """A running licence, in a room, that expires ``expires_in_days`` from today."""
    device = Device.objects.create(
        is_licence=True,
        contract_start_date=TODAY - datetime.timedelta(days=30),
        contract_expiration_date=TODAY + datetime.timedelta(days=expires_in_days),
    )
    room, _ = Room.objects.get_or_create(number="A1.23")
    InRoomRecord.objects.create(device=device, room=room)
    return device


def _state(device):
    return LicenceRecord.objects.get(device=device).license_state


@pytest.mark.django_db
def test_running_licence_is_expiring_within_the_window():
    assert _state(_licence(EXPIRING_WITHIN_DAYS)) == "expiring"
    assert _state(_licence(1)) == "expiring"


@pytest.mark.django_db
def test_running_licence_is_active_before_the_window_and_expired_after_expiry():
    assert _state(_licence(EXPIRING_WITHIN_DAYS + 1)) == "active"
    assert _state(_licence(0)) == "expired"


@pytest.mark.django_db
def test_removed_licence_is_not_listed():
    device = _licence(EXPIRING_WITHIN_DAYS + 1)
    RemovedRecord.objects.create(device=device)
    assert not LicenceRecord.objects.filter(device=device).exists()
