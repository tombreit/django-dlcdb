# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The iCal export of a licence: one all-day event per contract date.
"""

import datetime

import icalendar
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from dlcdb.core.models import Device


def _events(client, licence):
    """The calendar's events by type ("start", "expiry"), the prefix of their UID."""
    client.force_login(get_user_model().objects.create_superuser(email="admin@example.com", password="secret"))
    response = client.get(reverse("licenses:license_calendar", args=[licence.uuid]))
    assert response.status_code == 200
    calendar = icalendar.Calendar.from_ical(response.content)
    return {str(event["uid"]).split("-", 1)[0]: event for event in calendar.walk("VEVENT")}


@pytest.mark.django_db
def test_each_contract_date_is_an_all_day_event(client):
    licence = Device.objects.create(
        is_licence=True,
        contract_start_date=datetime.date(2026, 1, 1),
        contract_expiration_date=datetime.date(2027, 3, 31),
    )

    events = _events(client, licence)

    assert events["start"].decoded("dtstart") == datetime.date(2026, 1, 1)
    assert events["start"].decoded("dtend") == datetime.date(2026, 1, 2)
    assert events["expiry"].decoded("dtstart") == datetime.date(2027, 3, 31)
    assert events["expiry"].decoded("dtend") == datetime.date(2027, 4, 1)


@pytest.mark.django_db
def test_an_expiry_on_the_last_date_has_no_end(client):
    # 9999-12-31 has no next day; an all-day event without DTEND lasts one day.
    licence = Device.objects.create(
        is_licence=True,
        contract_start_date=datetime.date(2026, 1, 1),
        contract_expiration_date=datetime.date.max,
    )

    expiry = _events(client, licence)["expiry"]

    assert expiry.decoded("dtstart") == datetime.date.max
    assert "dtend" not in expiry
