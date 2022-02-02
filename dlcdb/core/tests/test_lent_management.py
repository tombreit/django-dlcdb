import pytest

from dlcdb.core.models import Device, Room, Person, LentRecord, InRoomRecord, Record
from dlcdb.core.tests import basetest


class LentManagementTests(basetest.BaseTest):

    def test(self):
        room = Room(number=234, nickname='Theke')
        room.save()

        for i in range(0, 5):
            device = self._create_device()
            device.is_lentable = True
            device.save()

            inroom = InRoomRecord(device=device)
            inroom.save()

        p1 = Person(first_name='Max', last_name='Mustermann')
        p1.save()

        p2 = Person(first_name='Sabine', last_name='Mustermann')
        p2.save()

        # device_1 = Device.objects.all().first()

        lent_record = LentRecord(person=p1, device=device)
        lent_record.save()
