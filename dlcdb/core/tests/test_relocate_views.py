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
from django.urls import reverse

from dlcdb.core.forms.adminactions_forms import RelocateActionForm
from dlcdb.core.models import Device, DeviceType, InRoomRecord, Record, Room
from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


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
def device(rooms, tenant):
    room_a, _ = rooms
    device = Device.objects.create(edv_id="EDV-ADMIN-MOVE", sap_id="8-8", tenant=tenant)
    InRoomRecord.objects.create(device=device, room=room_a)
    device.refresh_from_db()
    return device


@pytest.fixture
def relocator(make_user, tenant):
    """A user of `tenant` with the given core permissions."""

    def _make(*codenames):
        return make_user(*(f"core.{codename}" for codename in codenames), tenants=(tenant,))

    return _make


def _payload(device, room, **extra):
    return {"devices": [device.pk], "device_ids": [device.pk], "new_room": room.pk, **extra}


# --- the guard -----------------------------------------------------------


def test_anonymous_is_refused(client, url):
    # An unauthorized request is a 403 whatever the reason; the 403 page offers
    # anonymous visitors a log-in link.
    assert client.get(url).status_code == 403


def test_a_logged_in_user_without_the_move_permission_is_refused(client, url, relocator):
    client.force_login(relocator())
    assert client.get(url).status_code == 403


def test_the_relocate_permission_opens_the_view(client, url, device, relocator):
    client.force_login(relocator("transition_can_relocate_device"))
    assert client.get(f"{url}?ids={device.pk}").status_code == 200


def test_a_bare_get_without_ids_does_not_error(client, url, relocator):
    """The admin action always sends ?ids=, but a hand-typed URL must not 500."""
    client.force_login(relocator("transition_can_relocate_device"))
    assert client.get(url).status_code == 200


# --- the move itself -----------------------------------------------------


def test_a_permitted_user_can_move_a_device(client, url, device, rooms, relocator):
    _, room_b = rooms
    client.force_login(relocator("transition_can_relocate_device"))

    client.post(f"{url}?ids={device.pk}", _payload(device, room_b))

    device.refresh_from_db()
    assert device.active_record.record_type == Record.INROOM
    assert device.active_record.room == room_b


# --- tenant and device-type reassignment are a separate competence -------


def test_device_type_is_left_alone_without_change_device(client, url, device, rooms, relocator):
    """Moving a device is not licence to re-file it.

    Changing the device type is a plain device edit, so it needs
    ``core.change_device`` on top of the move permission. The relocation itself
    still goes through -- the user asked for something they may do and something
    they may not, and only the latter is dropped.
    """
    _, room_b = rooms
    device_type = DeviceType.objects.create(name="Beamer", prefix="BMR")
    original_type = device.device_type
    client.force_login(relocator("transition_can_relocate_device"))

    client.post(f"{url}?ids={device.pk}", _payload(device, room_b, new_device_type=device_type.pk))

    device.refresh_from_db()
    assert device.device_type == original_type
    assert device.active_record.room == room_b  # the move still happened


def test_a_single_tenant_user_gets_no_tenant_choice(client, url, device, rooms, relocator, tenant):
    """With only one tenant there is nothing to change to: the field is gone,
    and a crafted ``new_tenant`` is ignored while the move still happens."""
    _, room_b = rooms
    other = Tenant.objects.create(name="OtherTenant")
    client.force_login(relocator("transition_can_relocate_device", "change_device"))

    assert "new_tenant" not in client.get(f"{url}?ids={device.pk}").context["form"].fields

    client.post(f"{url}?ids={device.pk}", _payload(device, room_b, new_tenant=other.pk))

    device.refresh_from_db()
    assert device.tenant == tenant
    assert device.active_record.room == room_b


def test_a_crafted_id_of_a_foreign_device_is_ignored(client, url, device, rooms, relocator):
    room_a, room_b = rooms
    foreign = Device.objects.create(edv_id="EDV-FOREIGN", tenant=Tenant.objects.create(name="OtherTenant"))
    InRoomRecord.objects.create(device=foreign, room=room_a)
    client.force_login(relocator("transition_can_relocate_device"))

    client.post(f"{url}?ids={foreign.pk}", _payload(foreign, room_b))

    foreign.refresh_from_db()
    assert foreign.active_record.room == room_a


def test_the_tenant_choice_is_limited_to_the_users_tenants(tenant):
    other = Tenant.objects.create(name="OtherTenant")
    foreign = Tenant.objects.create(name="ForeignTenant")

    def form(new_tenant):
        return RelocateActionForm({"new_tenant": new_tenant.pk}, tenants=(tenant, other))

    assert form(other).is_valid()
    assert "new_tenant" in form(foreign).errors


def test_change_device_permits_the_reassignment(client, url, device, rooms, relocator):
    _, room_b = rooms
    device_type = DeviceType.objects.create(name="Beamer", prefix="BMR")
    client.force_login(relocator("transition_can_relocate_device", "change_device"))

    client.post(
        f"{url}?ids={device.pk}",
        _payload(device, room_b, new_device_type=device_type.pk),
    )

    device.refresh_from_db()
    assert device.device_type == device_type
    assert device.active_record.room == room_b
