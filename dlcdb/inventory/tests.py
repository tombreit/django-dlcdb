import pytest

from dlcdb.core.models import Inventory, Device, InRoomRecord, Room


@pytest.fixture
def inventory_1(db) -> Inventory:
    inventory = Inventory.objects.create(name="inventory_1", is_active=True)
    return inventory

@pytest.fixture
def inventory_2(db) -> Inventory:
    inventory = Inventory.objects.create(name="inventory_2", is_active=True)
    return inventory

@pytest.fixture
def inventory_3(db) -> Inventory:
    inventory = Inventory.objects.create(name="inventory_3", is_active=True)
    return inventory

@pytest.fixture
def device_1(db) -> Device:
    device = Device.objects.create(sap_id="123")
    return device

@pytest.fixture
def room_1(db) -> Room:
    room = Room.objects.create(number="456")
    return room

@pytest.mark.django_db
def test_inventory_unset_other_active_inventories(inventory_1, inventory_2, inventory_3):
    assert all([
        Inventory.objects.get(name="inventory_1").is_active is False,
        Inventory.objects.get(name="inventory_2").is_active is False,
    ])

@pytest.mark.django_db
def test_inventory_only_one_active_inventory(inventory_1, inventory_2, inventory_3):
    assert Inventory.objects.filter(is_active=True).count() == 1

@pytest.mark.django_db
def test_device_in_inventory_devices_for_room(device_1, room_1):
    device_record = InRoomRecord.objects.create(device=device_1, room=room_1)
    devices_in_room = Inventory.objects.devices_for_room(room_pk=room_1.pk, tenant=None, is_superuser=True)
    assert device_1 in devices_in_room
