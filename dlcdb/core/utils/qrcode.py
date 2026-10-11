# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The QR code of a device or a room: an SVG encoding its uuid, which
``Device.save()`` and ``Room.save()`` store and the inventory scanner reads.
"""

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
    qr_filename = f"{qr_text}.svg"
    qr_fileobj = segno.make(qr_text)

    _fileobj_io = BytesIO()
    qr_fileobj.save(_fileobj_io, "SVG")
    qr_fileobj = ContentFile(_fileobj_io.getvalue())

    return qrcode(qr_filename, qr_fileobj)
