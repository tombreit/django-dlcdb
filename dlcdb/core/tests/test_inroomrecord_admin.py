# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The room-assignment admin form (``InRoomRecordAdmin``) warns when the device it is
opened for is lent out right now: locating it would end the lending.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from dlcdb.core.models import Device, InRoomRecord, LentRecord, Person, Room
from dlcdb.core.tests.testingutils import establish_state

WARNING = "ist aktuell verliehen an"


@pytest.fixture
def helpdesk_client(client, plain_static, join_tenant):
    client.force_login(
        join_tenant(get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret"))
    )
    return client


@pytest.fixture
def device(tenant):
    return Device.objects.create(edv_id="EDV-1", is_lentable=True, tenant=tenant)


@pytest.fixture
def room(db):
    return Room.objects.create(number="A1.23")


def _lend(device, room, **fields):
    return establish_state(
        LentRecord,
        device=device,
        person=Person.objects.create(first_name="Max", last_name="Mustermann"),
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2026, 12, 31),
        **fields,
    )


def _add_form(client, device):
    return client.get(reverse("admin:core_inroomrecord_add"), {"device": device.pk}).content.decode()


@pytest.mark.django_db
def test_a_lent_device_shows_the_warning_with_lender_and_lending(helpdesk_client, device, room):
    lending = _lend(device, room)

    content = _add_form(helpdesk_client, device)

    assert f"{WARNING} <b>Mustermann, Max</b>" in content
    assert reverse("admin:core_lentrecord_change", args=[lending.pk]) in content


@pytest.mark.django_db
def test_a_returned_lending_shows_no_warning(helpdesk_client, device, room):
    _lend(device, room, lent_end_date=datetime.date(2026, 6, 1))

    assert WARNING not in _add_form(helpdesk_client, device)


@pytest.mark.django_db
def test_a_device_in_a_room_shows_no_warning(helpdesk_client, device, room):
    InRoomRecord.objects.create(device=device, room=room)

    assert WARNING not in _add_form(helpdesk_client, device)
