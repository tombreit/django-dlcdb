# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The lending admin's redirect after a lend: to the new LENT record, which only the
request that created it knows about.
"""

import datetime

import pytest
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import reverse

from dlcdb.core.models import Device, InRoomRecord, LentRecord, Person, Room


@pytest.fixture
def helpdesk(db, join_tenant):
    return join_tenant(get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret"))


@pytest.fixture
def lending_rooms(db):
    return {
        "desk": Room.objects.create(number="A1.23"),
        # LentRecord.clean() requires an auto-return room.
        "return": Room.objects.create(number="RETURN", is_auto_return_room=True),
    }


@pytest.fixture
def person(db):
    return Person.objects.create(first_name="Max", last_name="Mustermann")


def _available_device(edv_id, tenant, room):
    device = Device.objects.create(edv_id=edv_id, is_lentable=True, tenant=tenant)
    InRoomRecord.objects.create(device=device, room=room)
    device.refresh_from_db()
    return device


def _admin_request(user):
    request = RequestFactory().post("/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def _filled_lend_form(device, person, room):
    """The device's INROOM record as the admin change form hands it to save_model()."""
    obj = LentRecord.objects.get(pk=device.active_record.pk)
    obj.person = person
    obj.room = room
    obj.lent_start_date = datetime.date(2026, 6, 1)
    obj.lent_desired_end_date = datetime.date(2026, 7, 1)
    return obj


@pytest.mark.django_db
def test_interleaved_lends_each_redirect_to_their_own_lending(helpdesk, tenant, lending_rooms, person):
    """
    Two lends whose requests overlap: the first must still redirect to its own
    new lending, not to the one the second request created in between.
    """
    model_admin = admin_site._registry[LentRecord]
    device_a = _available_device("EDV-A", tenant, lending_rooms["desk"])
    device_b = _available_device("EDV-B", tenant, lending_rooms["desk"])
    request_a, obj_a = _admin_request(helpdesk), _filled_lend_form(device_a, person, lending_rooms["desk"])
    request_b, obj_b = _admin_request(helpdesk), _filled_lend_form(device_b, person, lending_rooms["desk"])

    model_admin.save_model(request_a, obj_a, form=None, change=True)
    model_admin.save_model(request_b, obj_b, form=None, change=True)
    response_a = model_admin.response_change(request_a, obj_a)

    device_a.refresh_from_db()
    assert device_a.active_record.record_type == LentRecord.LENT
    assert response_a.url == reverse("admin:core_lentrecord_change", args=[device_a.active_record.pk])


@pytest.mark.django_db
def test_lend_redirects_to_the_new_lending_and_an_edit_stays_on_it(
    client, plain_static, helpdesk, tenant, lending_rooms, person
):
    device = _available_device("EDV-LEND", tenant, lending_rooms["desk"])
    payload = {
        "person": person.pk,
        "room": lending_rooms["desk"].pk,
        "lent_start_date": "2026-06-01",
        "lent_desired_end_date": "2026-07-01",
        "lent_accessories": "",
        "lent_note": "",
        "_save": "",
    }
    client.force_login(helpdesk)

    response = client.post(reverse("admin:core_lentrecord_change", args=[device.active_record.pk]), payload)

    device.refresh_from_db()
    lending_url = reverse("admin:core_lentrecord_change", args=[device.active_record.pk])
    assert device.active_record.record_type == LentRecord.LENT
    assert response.status_code == 302
    assert response.url == lending_url

    response = client.post(lending_url, {**payload, "lent_note": "edited"})

    assert response.status_code == 302
    assert response.url == lending_url
    device.refresh_from_db()
    assert device.active_record.lent_note == "edited"
