# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import pytest
from django.core.exceptions import ValidationError
from dlcdb.core.models import Record, LentRecord, InRoomRecord, RemovedRecord, LostRecord, Person, Device
from django.utils import timezone


@pytest.mark.django_db
def test_is_active(room, lentable_device):
    assert Record.objects.filter(device=lentable_device).count() == 0

    # print("record: ", Record.objects.filter(device=lentable_device))

    inroom = InRoomRecord.objects.create(device=lentable_device, room=room)
    assert InRoomRecord.objects.get(pk=inroom.pk).is_active

    lent = LentRecord.objects.create(device=lentable_device)

    # for r in Record.objects.filter(device=lentable_device):
    #     print("record: ", r.pk, r.is_active, r.__class__)
    #
    # print("inroom: ", inroom.pk, inroom.is_active, inroom.__class__,)
    # print("lent: ", lent.pk, lent.is_active, lent.__class__)

    # Um die Record zu vergleicchen, muss die aktuelle Version aus der
    # Datenbank geholt werden.
    assert not Record.objects.get(pk=inroom.pk).is_active
    assert Record.objects.get(pk=lent.pk).is_active

    assert not InRoomRecord.objects.get(pk=inroom.pk).is_active
    assert LentRecord.objects.get(pk=lent.pk).is_active


@pytest.mark.django_db
def test_get_current_record(lentable_device, room):
    # ein frisch angelegtes Device hat keinen Record
    assert lentable_device.active_record is None

    inroom_record = InRoomRecord.objects.create(device=lentable_device, room=room)

    # print("inroom_record: ", type(inroom_record), inroom_record.__class__)

    current_record = lentable_device.active_record

    # print("current_record: ", type(current_record), current_record.__class__)

    # Tests if current_record is not an interable
    with pytest.raises(TypeError):
        iter(current_record)

    assert isinstance(current_record, InRoomRecord)
    assert not isinstance(current_record, LentRecord)
    assert isinstance(current_record, Record)

    assert current_record.is_active

    assert current_record.pk == inroom_record.pk


@pytest.mark.django_db
def test_has_active_record_set(room, lentable_device):
    inroom = InRoomRecord.objects.create(device=lentable_device, room=room)

    assert lentable_device.active_record.pk == inroom.pk
    assert lentable_device.active_record.pk == Record.objects.get(device=lentable_device, is_active=True).pk

    lent = LentRecord.objects.create(device=lentable_device)

    assert lentable_device.active_record.pk != inroom.pk
    assert lentable_device.active_record.pk == lent.pk
    assert lentable_device.active_record.pk == Record.objects.get(device=lentable_device, is_active=True).pk


@pytest.mark.django_db
def test_get_proxy_instance(plain_device):
    """
    Tests the get_proxy_instance method. Ensures that the correct type is returned.
    :return:
    """
    record = InRoomRecord.objects.create(device=plain_device)

    assert isinstance(record.get_proxy_instance(), InRoomRecord)

    assert not isinstance(record.get_proxy_instance(), LentRecord)

    assert record.get_proxy_instance().__class__ != Record


# rewrite test to capture the ValidationError in the model.clean() method (and not in the model.save() method)
@pytest.mark.skip
@pytest.mark.django_db
def test_is_proxy_model(plain_device):
    # Creating records via proxy records interface is allowed:
    proxy_record = InRoomRecord.objects.create(device=plain_device)
    assert proxy_record._meta.proxy

    # Creating plain record instances is not allowed:
    with pytest.raises(ValidationError):
        Record.objects.create(device=plain_device, record_type="ORDERED")


@pytest.mark.django_db
def test_removed_or_lost_record_has_no_room(room, device_1):
    inroom = InRoomRecord.objects.create(device=device_1, room=room)
    # print(f"{device_1.active_record.room=}")
    assert inroom.room == room
    assert device_1.active_record.room == room

    lost = LostRecord.objects.create(device=device_1)
    # print(f"{device_1.active_record.room=}")
    assert lost.room is None
    assert device_1.active_record.room is None

    inroom2 = InRoomRecord.objects.create(device=device_1, room=room)
    # print(f"{device_1.active_record.room=}")
    assert inroom2.room == room
    assert device_1.active_record.room == room

    removed = RemovedRecord.objects.create(device=device_1)
    # print(f"{device_1.active_record.room=}")
    assert removed.room is None
    assert device_1.active_record.room is None


@pytest.mark.django_db
def test_get_last_found_returns_latest_found_record():
    # Create a device
    device = Device.objects.create(sap_id="12345", series="A")

    # Create a person for lending
    person = Person.objects.create(first_name="John", last_name="Doe", email="john@example.com")

    _now = timezone.now()
    old_timestamp = _now - timezone.timedelta(days=60)
    recent_timestamp = _now - timezone.timedelta(days=30)
    most_recent_timestamp = _now - timezone.timedelta(days=1)

    # Create two found records: one INROOM, one LENT
    # As the `creatd_at` field is set to auto_now, we need to overwrite
    # it manually
    inroom_record = InRoomRecord.objects.create(
        device=device,
    )
    inroom_record.created_at = old_timestamp
    inroom_record.save(update_fields=["created_at"])

    lent_record = LentRecord.objects.create(
        device=device,
        person=person,
    )
    lent_record.created_at = recent_timestamp
    lent_record.save(update_fields=["created_at"])

    # The lent_record should be the most recent one
    assert recent_timestamp == device.active_record.get_last_found()

    _lost_record = LostRecord.objects.create(
        device=device,
    )

    # Even after setting the device as lost, the last lent_record
    # should still be the most recent round record
    assert recent_timestamp == device.active_record.get_last_found()

    inroom_record = InRoomRecord.objects.create(
        device=device,
    )
    inroom_record.created_at = most_recent_timestamp
    inroom_record.save(update_fields=["created_at"])

    # Now the inroom_record should be the most recent found record
    assert most_recent_timestamp == device.active_record.get_last_found()
