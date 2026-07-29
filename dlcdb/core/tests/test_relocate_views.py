# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for ``DevicesRelocateView``, the admin bulk relocate action's landing page.

The view had no tests and no permission check: any logged-in user who knew the
URL could POST device ids and write InRoomRecords, reassign tenants and change
device types. Its frontend twin (``assets.views.relocate``) has always required a
permission, so this closes the asymmetry.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from dlcdb.core.models import Device, DeviceType, InRoomRecord, Record, Room
from dlcdb.tenants.models import Tenant

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def plain_static(settings):
    """Plain static storage so tests do not require a built staticfiles manifest."""
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def url():
    return reverse("core:core_devices_relocate")


@pytest.fixture
def rooms():
    return Room.objects.create(number="A1.01"), Room.objects.create(number="B2.02")


@pytest.fixture
def device(rooms):
    room_a, _ = rooms
    device = Device.objects.create(edv_id="EDV-ADMIN-MOVE", sap_id="8-8")
    InRoomRecord.objects.create(device=device, room=room_a)
    device.refresh_from_db()
    return device


@pytest.fixture
def make_user(db):
    def _make(*codenames, email="admin-mover@example.com"):
        user = get_user_model().objects.create_user(email=email, password="secret", username=email.split("@")[0])
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="core"))
        return get_user_model().objects.get(pk=user.pk)  # reset the perm cache

    return _make


def _payload(device, room, **extra):
    return {"devices": [device.pk], "device_ids": [device.pk], "new_room": room.pk, **extra}


# --- the guard -----------------------------------------------------------


def test_anonymous_is_sent_to_the_login_page(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_a_logged_in_user_without_the_move_permission_is_refused(client, url, make_user):
    client.force_login(make_user())
    assert client.get(url).status_code == 403


def test_the_relocate_permission_opens_the_view(client, url, device, make_user):
    client.force_login(make_user("can_relocate_device"))
    assert client.get(f"{url}?ids={device.pk}").status_code == 200


def test_a_bare_get_without_ids_does_not_error(client, url, make_user):
    """The admin action always sends ?ids=, but a hand-typed URL must not 500."""
    client.force_login(make_user("can_relocate_device"))
    assert client.get(url).status_code == 200


# --- the move itself -----------------------------------------------------


def test_a_permitted_user_can_move_a_device(client, url, device, rooms, make_user):
    _, room_b = rooms
    client.force_login(make_user("can_relocate_device"))

    client.post(f"{url}?ids={device.pk}", _payload(device, room_b))

    device.refresh_from_db()
    assert device.active_record.record_type == Record.INROOM
    assert device.active_record.room == room_b


# --- tenant and device-type reassignment are a separate competence -------


def test_device_type_is_left_alone_without_change_device(client, url, device, rooms, make_user):
    """Moving a device is not licence to re-file it.

    Changing the device type is a plain device edit, so it needs
    ``core.change_device`` on top of the move permission. The relocation itself
    still goes through -- the user asked for something they may do and something
    they may not, and only the latter is dropped.
    """
    _, room_b = rooms
    device_type = DeviceType.objects.create(name="Beamer", prefix="BMR")
    original_type = device.device_type
    client.force_login(make_user("can_relocate_device"))

    client.post(f"{url}?ids={device.pk}", _payload(device, room_b, new_device_type=device_type.pk))

    device.refresh_from_db()
    assert device.device_type == original_type
    assert device.active_record.room == room_b  # the move still happened


def test_a_non_superuser_cannot_reassign_the_tenant(client, url, device, rooms, make_user):
    """Pre-existing rule, pinned: the form refuses a tenant change outright.

    Tenant reassignment moves a device between organisational scopes, so it is
    superuser-only at form level and never reaches the view's permission check.
    """
    _, room_b = rooms
    tenant = Tenant.objects.create(name="OtherTenant")
    client.force_login(make_user("can_relocate_device", "change_device"))

    response = client.post(f"{url}?ids={device.pk}", _payload(device, room_b, new_tenant=tenant.pk))

    assert not response.context["form"].is_valid()
    assert "new_tenant" in response.context["form"].errors
    device.refresh_from_db()
    assert device.tenant is None


def test_change_device_permits_the_reassignment(client, url, device, rooms, make_user):
    _, room_b = rooms
    device_type = DeviceType.objects.create(name="Beamer", prefix="BMR")
    client.force_login(make_user("can_relocate_device", "change_device"))

    client.post(
        f"{url}?ids={device.pk}",
        _payload(device, room_b, new_device_type=device_type.pk),
    )

    device.refresh_from_db()
    assert device.device_type == device_type
    assert device.active_record.room == room_b
