# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The inventory scan of one room: what the room page submits for each scanned or
listed device, applied in one atomic batch.

- found: the device is in this room now; ``lifecycle.localise`` puts it here
  with the current inventory's stamp;
- not found: a lent device moves to the external room (``relocate_lending``),
  any other device is lost (``transition_lose``);
- unknown: the device is localised here without a stamp, and existing stamps
  of the current inventory are removed.

The rules are lifecycle calls; this module is the inventory app's workflow.
"""

import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from dlcdb.core import lifecycle
from dlcdb.core.models import Device, Inventory, Note, Record, Room

from .utils import update_inventory_note


def _found_inventory_note(active_record):
    """The audit note stamped on the new INROOM record when a device is found,
    describing where it came back from."""
    record_type = getattr(active_record, "record_type", None)
    if record_type == Record.LOST:
        return "Was: LOST, now: INROOM, cause: INVENTORY"
    if record_type == Record.REMOVED:
        return "Was: REMOVED, now: INROOM, cause: INVENTORY"
    return ""


@transaction.atomic
def inventorize_uuids_for_room(*, uuids, room_pk, user):
    """
    Main inventorization method: Expects a list of device uuids,
    an inventory status for each uuid and a room and sets an
    appropriate inventory record.
    """
    try:
        room = Room.objects.get(pk=room_pk)
    except Room.DoesNotExist:
        raise ObjectDoesNotExist(
            f"Something went wrong. A room with pk={room_pk} does not exist. Please contact your it staff."
        )

    try:
        external_room = Room.objects.get(is_external=True)
    except Room.DoesNotExist:
        raise ObjectDoesNotExist("No room is flagged with 'is_external'. Please contact your it staff.")

    current_inventory = Inventory.objects.active_inventory()
    uuids_states_dict = json.loads(uuids)

    for uuid, state in uuids_states_dict.items():
        try:
            device = Device.objects.get(uuid=uuid)
        except Device.DoesNotExist as does_not_exist:
            raise ObjectDoesNotExist(f"No device for uuid {uuid}! {does_not_exist}")

        active_record = device.active_record

        if state == "dev_state_found":
            # The device is here now: localise it in this room and stamp the
            # inventory. lifecycle.localise picks the right transition for the
            # device's current state (relocate / find / recover / locate), so
            # a found LOST/REMOVED device is brought back to INROOM and its
            # stale removal fields are cleared by the proxy's save().
            note = _found_inventory_note(active_record)
            lifecycle.localise(device, room=room, user=user, inventory=current_inventory, note=note)

        elif state == "dev_state_notfound":
            # A lent device missing from its room is with its borrower, not
            # lost: keep the lending, just move it to the external room.
            if (
                active_record is not None
                and active_record.record_type == Record.LENT
                and active_record.room != external_room
            ):
                previous_room = active_record.room
                lifecycle.relocate_lending(active_record, room=external_room, user=user)

                lent_not_found_msg = (
                    f"Lented asset not found in expected location `{previous_room}. Changed to `{active_record.room}`."
                )
                note_obj, _note_obj_created = Note.objects.get_or_create(
                    inventory=current_inventory,
                    device=active_record.device,
                )
                note_obj.text = f"{note_obj.text} *** {lent_not_found_msg}"
                note_obj.save()
            else:
                lifecycle.transition_lose(device, inventory=current_inventory, user=user)

        elif state == "dev_state_unknown":
            # A device added to a room but marked neither found nor not-found,
            # or an already-inventorized device re-marked "unknown": localise
            # it in the room but WITHOUT an inventory stamp, and strip any
            # existing stamp so it no longer counts as inventorized.
            already_inventorized_records = device.get_current_inventory_records
            if already_inventorized_records:
                # Save one at a time (not a bulk update) so Record.save() runs.
                for _record in already_inventorized_records:
                    _record.inventory = None
                    _record.save()

                msg = f"Device marked as 'unknown state' during inventory by {user}. Removed existing inventory stamp."
                update_inventory_note(inventory=current_inventory, device=device, msg=msg)

            lifecycle.localise(
                device,
                room=room,
                user=user,
                inventory=None,
                note="Marked as 'unknown state' during inventory.",
            )

        else:
            raise RuntimeError(f"This should never happen: given state `{state}` not recognized! Raising 500.")
