# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json

import pytest

from dlcdb.core.models import Inventory, InRoomRecord, Record, Note
from dlcdb.inventory.utils import update_inventory_note


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
    _device_record_1 = InRoomRecord.objects.create(device=device_1, room=room_1)
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
    # has an inventory stamp
    device_record_1_1 = InRoomRecord.objects.create(device=device_1, room=room_2)

    # Reload old record from db to get changes (is_active)
    device_record_1 = Record.objects.get(id=device_record_1.id)

    assert device_1.active_record == device_record_1_1


@pytest.mark.django_db
def test_update_inventory_note(device_1, inventory_1):
    # Test creating new note
    msg1 = "First test message"
    note1 = update_inventory_note(inventory=inventory_1, device=device_1, msg=msg1)

    assert note1.text == msg1
    assert Note.objects.count() == 1
    assert note1.inventory == inventory_1
    assert note1.device == device_1

    # Test appending to existing note
    msg2 = "Second test message"
    note2 = update_inventory_note(inventory=inventory_1, device=device_1, msg=msg2)

    assert note2.text == f"{msg1}; {msg2}"
    assert Note.objects.count() == 1
    assert note2.id == note1.id


@pytest.mark.django_db
def test_inventorize_uuids_for_room(device_1, device_2, room_1, external_room, inventory_1, user):
    # Create records
    _device_1_record_1 = InRoomRecord.objects.create(device=device_1, room=room_1)
    device_1_record_2 = InRoomRecord.objects.create(device=device_1, room=external_room)

    device_2_record_1 = InRoomRecord.objects.create(device=device_2, room=room_1)

    # Create test data - device states dict as JSON
    uuids_states = {
        str(device_1.uuid): "dev_state_found",
        str(device_2.uuid): "dev_state_notfound",
    }

    # As inventorize_uuids_for_room adds new records, we check the current
    # active_record of the device before the inventory
    assert device_1.active_record.pk == device_1_record_2.pk
    assert device_2.active_record.pk == device_2_record_1.pk

    # Test successful inventory
    Inventory.inventorize_uuids_for_room(uuids=json.dumps(uuids_states), room_pk=external_room.pk, user=user)

    # Verify device_1 was marked as found
    device_1.refresh_from_db()
    assert device_1.active_record.room == external_room
    assert device_1.active_record.inventory == inventory_1
    assert device_1.active_record.record_type == Record.INROOM

    # Verify device_2 was marked as lost
    device_2.refresh_from_db()
    assert device_2.active_record.record_type == Record.LOST
    assert device_2.active_record.inventory == inventory_1


@pytest.mark.django_db
def test_inventorize_uuids_unknown(device_1, room_1, external_room, inventory_1, user):
    # Create multiple inventorized records
    device_record_1 = InRoomRecord.objects.create(device=device_1, room=room_1, inventory=inventory_1)
    device_record_2 = InRoomRecord.objects.create(device=device_1, room=external_room, inventory=inventory_1)

    # Confirm this device counts as inventorized
    inventorized_records = device_1.get_current_inventory_records
    assert inventorized_records.count() == 2
    assert device_record_1 in inventorized_records
    assert device_record_2 in inventorized_records

    # Test unknown state
    uuids_states_unknown_state = {str(device_1.uuid): "dev_state_unknown"}
    Inventory.inventorize_uuids_for_room(uuids=json.dumps(uuids_states_unknown_state), room_pk=room_1.pk, user=user)

    # Verify device with unknown state
    device_1.refresh_from_db()
    assert device_1.get_current_inventory_records.count() == 0
    # assert "unknown state" in device_1.active_record.note

    # Ensure an inventory audit log message was created or updated
    inventory_note = Note.objects.filter(device=device_1, inventory=inventory_1)
    assert inventory_note.exists()
    assert inventory_note.count() == 1

    assert f"Device marked as 'unknown state' during inventory by {user}." in inventory_note.get().text
