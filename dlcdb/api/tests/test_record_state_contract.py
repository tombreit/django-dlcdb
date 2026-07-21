# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for the record state as a *public* contract.

The read-only API v2 exposes ``record_type`` verbatim -- both as a serialised
value and as the ``active_record__record_type`` query filter. Together with the
DB CheckConstraint (``core/migrations/0060_*``) this pins the state keys down:
a consolidated FSM may reorganise transitions freely, but renaming or dropping a
state would break external consumers.

This is the one place where exact equality on the state keys is the right
assertion, rather than the subset checks used elsewhere.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from dlcdb.core.models import Device, InRoomRecord, LentRecord, Person, Record, Room
from dlcdb.core.models.record import RECORD_TYPE_KEYS

pytestmark = pytest.mark.django_db


EXPECTED_STATE_KEYS = {"ORDERED", "INROOM", "LENT", "LOST", "REMOVED"}


@pytest.fixture
def api_client(db):
    from rest_framework.test import APIClient

    user = get_user_model().objects.create_user(email="api@example.com", password="secret")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def devices(db):
    room = Room.objects.create(number="API-1")
    person = Person.objects.create(first_name="Max", last_name="Mustermann")

    located = Device.objects.create(edv_id="EDV-API-INROOM")
    InRoomRecord.objects.create(device=located, room=room)

    lent = Device.objects.create(edv_id="EDV-API-LENT", is_lentable=True)
    LentRecord.objects.create(
        device=lent,
        person=person,
        room=room,
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )

    return {"located": located, "lent": lent, "room": room, "person": person}


def test_state_keys_are_frozen():
    """
    Exact equality on purpose: these strings are baked into the DB
    CheckConstraint and into the public API contract.
    """
    assert set(RECORD_TYPE_KEYS) == EXPECTED_STATE_KEYS


def test_api_serialises_the_raw_state_code(api_client, devices):
    """
    The API returns the stable key ``"INROOM"``, never the translated display
    label ``"In room"``. Consumers match on the code, so the contract does not
    move when a label is retranslated.
    """
    url = reverse("device-detail", kwargs={"uuid": devices["located"].uuid})
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["record_type"] == Record.INROOM


def test_api_filters_devices_by_state(api_client, devices):
    response = api_client.get("/api/v2/devices/", {"active_record__record_type": Record.LENT})

    assert response.status_code == 200
    results = response.data["results"] if isinstance(response.data, dict) else response.data
    returned = {row["edv_id"] for row in results}
    assert returned == {"EDV-API-LENT"}


def test_api_state_filter_accepts_every_state_key(api_client, devices):
    """No state key may 400 the filter -- they are all part of the contract."""
    for key in RECORD_TYPE_KEYS:
        response = api_client.get("/api/v2/devices/", {"active_record__record_type": key})
        assert response.status_code == 200, f"filtering by {key} failed"


def test_api_requires_authentication():
    from rest_framework.test import APIClient

    response = APIClient().get("/api/v2/devices/")
    assert response.status_code in (401, 403)
