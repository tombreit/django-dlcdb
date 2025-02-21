# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from collections import namedtuple
from io import BytesIO

import segno

from django.conf import settings
from django.core.files.base import ContentFile


def uuid2qrcode(uuid, infix=None):
    qrcode = namedtuple("qrcode", ["filename", "fileobj"])

    uuid = str(uuid)  # Ensure uuid is a string and not an instance of UUID
    qr_text = "{prefix}{infix}{uuid}".format(
        uuid=uuid,
        prefix=settings.QRCODE_PREFIX,
        infix=infix if infix else "",
    )
    qr_filename = "{0}.svg".format(qr_text)
    qr_fileobj = segno.make(qr_text)

    _fileobj_io = BytesIO()
    qr_fileobj.save(_fileobj_io, "SVG")
    qr_fileobj = ContentFile(_fileobj_io.getvalue())

    return qrcode(qr_filename, qr_fileobj)


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

    inventory_note_obj, inventory_note_obj_created = Note.objects.get_or_create(
        inventory=inventory,
        device=device,
    )
    inventory_note_text = inventory_note_obj.text

    inventory_note_obj.text = f"{inventory_note_text}{'; ' if inventory_note_text else ''}{msg}"
    inventory_note_obj.save()

    return inventory_note_obj
