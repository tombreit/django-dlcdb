# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The iCal export of a licence: one all-day event per contract date, for the
licences of the user's tenants only.
"""

import datetime

import icalendar
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from dlcdb.core.models import Device
from dlcdb.tenants.models import Tenant


@pytest.fixture
def user(db, join_tenant):
    return join_tenant(get_user_model().objects.create_superuser(email="admin@example.com", password="secret"))


def _calendar(client, user, licence):
    client.force_login(user)
    return client.get(reverse("licenses:license_calendar", args=[licence.uuid]))


def _events(client, user, licence):
    """The calendar's events by type ("start", "expiry"), the prefix of their UID."""
    response = _calendar(client, user, licence)
    assert response.status_code == 200
    calendar = icalendar.Calendar.from_ical(response.content)
    return {str(event["uid"]).split("-", 1)[0]: event for event in calendar.walk("VEVENT")}


@pytest.mark.django_db
def test_each_contract_date_is_an_all_day_event(client, user, tenant):
    licence = Device.objects.create(
        is_licence=True,
        tenant=tenant,
        contract_start_date=datetime.date(2026, 1, 1),
        contract_expiration_date=datetime.date(2027, 3, 31),
    )

    events = _events(client, user, licence)

    assert events["start"].decoded("dtstart") == datetime.date(2026, 1, 1)
    assert events["start"].decoded("dtend") == datetime.date(2026, 1, 2)
    assert events["expiry"].decoded("dtstart") == datetime.date(2027, 3, 31)
    assert events["expiry"].decoded("dtend") == datetime.date(2027, 4, 1)


@pytest.mark.django_db
def test_an_expiry_on_the_last_date_has_no_end(client, user, tenant):
    # 9999-12-31 has no next day; an all-day event without DTEND lasts one day.
    licence = Device.objects.create(
        is_licence=True,
        tenant=tenant,
        contract_start_date=datetime.date(2026, 1, 1),
        contract_expiration_date=datetime.date.max,
    )

    expiry = _events(client, user, licence)["expiry"]

    assert expiry.decoded("dtstart") == datetime.date.max
    assert "dtend" not in expiry


@pytest.mark.django_db
def test_a_licence_of_another_tenant_is_not_found(client, user):
    licence = Device.objects.create(
        is_licence=True,
        tenant=Tenant.objects.create(name="Another tenant"),
        contract_start_date=datetime.date(2026, 1, 1),
    )

    assert _calendar(client, user, licence).status_code == 404
