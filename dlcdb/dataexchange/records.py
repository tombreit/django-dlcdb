# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Record creation for CSV device imports.
"""

from django.core.exceptions import ValidationError

from dlcdb.core.models import OrganizationalUnit, Record, Room

from .fields import create_fk_obj, get_or_create_person


def create_record(
    *,
    device,
    record_type,
    record_note,
    room,
    username,
    removed_date,
    user=None,
    lender_first_name=None,
    lender_last_name=None,
    lender_email=None,
    lender_ou=None,
    lent_start_date=None,
    lent_desired_end_date=None,
    lent_end_date=None,
    lent_note="",
    lent_reason="",
    lent_accessories="",
):
    from dlcdb.core.models import InRoomRecord, LentRecord, LostRecord, RemovedRecord

    # print(f"Creating record {record_type} for {device}...")
    # A single CSV row may yield more than one record: a completed loan
    # (LENT with a lent_end_date) produces a LENT record followed by an
    # INROOM record (the device is back). Records are returned in the order
    # they must be saved; the last one saved becomes the active record.
    records = []

    # A row with a room but no explicit record type means the device is in
    # that room.
    if not record_type and room:
        record_type = Record.INROOM

    # Fields shared by every record type. Type-specific fields (room, person,
    # lent_*, removed_date, ...) are added per branch.
    common = {
        "device": device,
        "username": username.strip() if username else "",
        "user": user,
        "note": record_note,
    }

    if record_type == Record.INROOM:
        if not room:
            raise ValidationError(f"No room number given for device {device} with record_type {record_type}!")

        room_obj = create_fk_obj(model_class=Room, instance_key="number", instance_value=room)
        records.append(InRoomRecord(**common, room=room_obj))

    elif record_type == Record.LOST:
        records.append(LostRecord(**common))

    elif record_type == Record.REMOVED:
        records.append(RemovedRecord(**common, removed_date=removed_date))

    elif record_type == Record.LENT:
        if not room:
            raise ValidationError(f"No room number given for device {device} with record_type {record_type}!")

        room_obj = create_fk_obj(model_class=Room, instance_key="number", instance_value=room)

        ou_obj = None
        if lender_ou:
            ou_obj = create_fk_obj(model_class=OrganizationalUnit, instance_key="name", instance_value=lender_ou)

        person_obj = get_or_create_person(
            first_name=lender_first_name,
            last_name=lender_last_name,
            email=lender_email,
            organizational_unit=ou_obj,
        )

        records.append(
            LentRecord(
                **common,
                room=room_obj,
                person=person_obj,
                lent_start_date=lent_start_date,
                lent_desired_end_date=lent_desired_end_date,
                lent_end_date=lent_end_date,
                lent_note=lent_note,
                lent_reason=lent_reason,
                lent_accessories=lent_accessories,
            )
        )

        # A returned loan (lent_end_date set) is already finished: the device
        # is back in its room, so follow the LENT record with an INROOM record
        # that becomes the active record.
        if lent_end_date:
            records.append(InRoomRecord(**common, room=room_obj))

    return records
