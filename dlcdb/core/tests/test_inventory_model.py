# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import pytest
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import translation

from dlcdb.core import lifecycle, models


class InventoryTests(TestCase):
    def test_set_active_logic(self):
        """
        Ensure that an inventory which is saved as active sets all other inventories to
        inactive.
        :return:
        """

        i1 = models.Inventory(name="2016", is_active=True)
        i1.save()

        i2 = models.Inventory(name="2017", is_active=True)
        i2.save()

        # very important to requery i1 in order to get the fresh new database representation of i1.
        # Otherwise i1 is outdated as the query of the is_active manipulation does not affect existing python objects.
        i1 = models.Inventory.objects.get(id=i1.id)
        self.assertFalse(i1.is_active)
        self.assertTrue(i2.is_active)


def _room_status(room, tenant):
    return models.Inventory.objects.tenant_aware_room_objects(tenants=[tenant]).get(pk=room.pk).get_inventory_status


@pytest.mark.django_db
def test_the_room_badge_counts_devices_not_records(tenant, user, room_1, room_2, inventory_1):
    """
    A scan appends a stamped record even when the device is already in the room, and
    a device found elsewhere leaves its stamped record behind. Neither may make a
    room look counted while devices in it were never scanned.
    """
    devices = {}
    for edv_id in ("SCANNED-TWICE", "NEVER-SCANNED-1", "NEVER-SCANNED-2", "MOVED-AWAY"):
        devices[edv_id] = models.Device.objects.create(edv_id=edv_id, tenant=tenant)
        models.InRoomRecord.objects.create(device=devices[edv_id], room=room_1)

    for _scan in range(2):
        lifecycle.localise(devices["SCANNED-TWICE"], room=room_1, user=user, inventory=inventory_1)
    lifecycle.localise(devices["MOVED-AWAY"], room=room_1, user=user, inventory=inventory_1)
    lifecycle.localise(devices["MOVED-AWAY"], room=room_2, user=user, inventory=inventory_1)

    assert _room_status(room_1, tenant).status_str == "inprogress"
    assert _room_status(room_1, tenant).n_of_ns == "1 / 3"
    assert _room_status(room_2, tenant).status_str == "completed"
    assert _room_status(room_2, tenant).n_of_ns == "1 / 1"


@pytest.mark.django_db
def test_the_room_badge_picks_colour_and_label_for_each_status(tenant, user, inventory_1):
    expected = {
        "completed": ("success", "Completed", 1, 1),
        "outstanding": ("warning", "Outstanding", 0, 1),
        "inprogress": ("primary", "In progress", 1, 2),
    }
    for status, (colour, label, counted, in_room) in expected.items():
        room = models.Room.objects.create(number=f"ROOM-{status}")
        for index in range(in_room):
            device = models.Device.objects.create(edv_id=f"{status}-{index}", tenant=tenant)
            models.InRoomRecord.objects.create(device=device, room=room)
            if index < counted:
                lifecycle.localise(device, room=room, user=user, inventory=inventory_1)
        room = models.Inventory.objects.tenant_aware_room_objects(tenants=[tenant]).get(pk=room.pk)

        with translation.override("en"):
            button = render_to_string("inventory/includes/inventory_status_badge.html", {"room": room})
            badge = render_to_string("inventory/includes/inventory_status_badge.html", {"room": room, "style": "badge"})

        assert f"btn-{colour}" in button and label in button
        assert f"text-bg-{colour}" in badge and f"{counted} / {in_room}" in badge
