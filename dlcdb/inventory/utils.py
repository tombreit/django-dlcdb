# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2


def unique_seq(sequence):
    """
    Eleminate duplicates in a list while preserving the order
    See: http://www.martinbroadhurst.com/removing-duplicates-from-a-list-while-preserving-order-in-python.html
    """
    seen = set()
    return [x for x in sequence if not (x in seen or seen.add(x))]


def update_inventory_note(*, inventory, device, msg):
    """
    Update or create an inventory note for a given device.
    If the note alreay exists, append the message to the existing note.
    """

    from dlcdb.core.models import Note

    inventory_note_obj, _inventory_note_obj_created = Note.objects.get_or_create(
        inventory=inventory,
        device=device,
    )
    inventory_note_text = inventory_note_obj.text

    inventory_note_obj.text = f"{inventory_note_text}{'; ' if inventory_note_text else ''}{msg}"
    inventory_note_obj.save()

    return inventory_note_obj
