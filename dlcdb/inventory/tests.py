# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import pytest

from dlcdb.core.models import Inventory, InRoomRecord, Device, Record


@pytest.mark.django_db
def test_inventory_unset_other_active_inventories(inventory_1, inventory_2, inventory_3):
    assert all(
        [
            Inventory.objects.get(name="inventory_1").is_active is False,
            Inventory.objects.get(name="inventory_2").is_active is False,
        ]
    )


@pytest.mark.django_db
def test_inventory_only_one_active_inventory(inventory_1, inventory_2, inventory_3):
    assert Inventory.objects.filter(is_active=True).count() == 1


@pytest.mark.django_db
def test_device_in_inventory_devices_for_room(device_1, room_1):
    devices_in_room = Inventory.objects.tenant_aware_device_objects_for_room(
        room_pk=room_1.pk, tenant=None, is_superuser=True
    )
    assert device_1 in devices_in_room


@pytest.mark.django_db
def test_if_device_counts_as_inventorized(device_1, device_2, room_1, room_2, inventory_1):
    device_record_1 = InRoomRecord.objects.create(device=device_1, room=room_1, inventory=inventory_1)
    assert device_record_1.device in Inventory.objects.inventory_relevant_devices(is_superuser=True)

    device_record_2 = InRoomRecord.objects.create(device=device_1, room=room_2, inventory=None)
    assert device_record_2.device in Inventory.objects.inventory_relevant_devices(is_superuser=True)

    test_dict_true = {
        "number": room_2.number,
        "room_devices_count": 1,
    }
    assert test_dict_true in Inventory.objects.tenant_aware_room_objects().values("number", "room_devices_count")

    test_dict_false = {
        "number": room_2.number,
        "room_devices_count": 2,
    }
    assert test_dict_false not in Inventory.objects.tenant_aware_room_objects().values("number", "room_devices_count")


@pytest.mark.django_db
def test_get_is_already_inventorized(device_1, device_2, room_1, room_2, inventory_1):
    assert device_2.get_current_inventory_record is None

    device_record_1 = InRoomRecord.objects.create(device=device_1, room=room_1, inventory=inventory_1)
    assert device_1.active_record.inventory == inventory_1
    assert device_1.get_current_inventory_record is not None
    assert isinstance(device_1.get_current_inventory_record, Record)

    # device_1 should count as inventorized, even if a later (not the active) record
    # has the inventory stamp
    device_record_1_1 = InRoomRecord.objects.create(device=device_1, room=room_2)

    # Reload old record from db to get changes (is_active)
    device_record_1 = Record.objects.get(id=device_record_1.id)

    assert device_1.active_record == device_record_1_1
    assert device_record_1.is_active is False
    assert device_record_1_1.is_active is True
    assert device_1.get_current_inventory_record is not None


@pytest.mark.django_db
def test_get_current_inventory_record(device_1, room_1, room_2, inventory_1):
    device_record_1 = InRoomRecord.objects.create(device=device_1, room=room_1, inventory=inventory_1)
    device_record_2 = InRoomRecord.objects.create(device=device_1, room=room_2, inventory=inventory_1)

    # Reload old record from db to get changes (is_active)
    device_record_1 = Record.objects.get(id=device_record_1.id)
    device_record_2 = Record.objects.get(id=device_record_2.id)
    device_1 = Device.objects.get(id=device_1.id)

    assert device_1.get_current_inventory_record == device_record_2
