# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Record creation for CSV device imports.
"""

from django.core.exceptions import ValidationError

from dlcdb.core.models import Record, Room

from .fields import create_fk_obj


def create_record(*, device, record_type, record_note, room, person, username, removed_date):
    from dlcdb.core.models import InRoomRecord, LostRecord, RemovedRecord

    # print(f"Creating record {record_type} for {device}...")
    record_obj = None

    if record_type == Record.INROOM:
        if not room:
            raise ValidationError(f"No room number given for device {device} with record_type {record_type}!")

        # room_obj, created = Room.objects.get_or_create(
        #     number__iexact=room,
        #     defaults={'number': room},
        # )
        room_obj = create_fk_obj(model_class=Room, instance_key="number", instance_value=room)

        record_obj = InRoomRecord(
            device=device,
            room=room_obj,
            note=record_note,
            username=username.strip() if username else "",
        )

    elif record_type == Record.LOST:
        record_obj = LostRecord(
            device=device,
            note=record_note,
            username=username.strip() if username else "",
        )

    elif record_type == Record.REMOVED:
        record_obj = RemovedRecord(
            device=device,
            note=record_note,
            removed_date=removed_date,
            username=username.strip() if username else "",
        )

    return record_obj
