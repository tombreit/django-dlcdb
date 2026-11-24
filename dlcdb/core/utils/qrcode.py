# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The QR code of a device or a room: an SVG encoding QRCODE_PREFIX, the infix of
its model (QRCODE_INFIXES) and its uuid. Printed labels carry it, the inventory
scanner reads it (``qr_inventorize.js``).
"""

from collections import namedtuple
from io import BytesIO

import segno
from django.conf import settings
from django.core.files.base import ContentFile


def payload(model_name, uuid):
    """The text a QR code encodes, e.g. "DLCDBD3f2c…" for a device."""
    return f"{settings.QRCODE_PREFIX}{settings.QRCODE_INFIXES[model_name]}{uuid}"


def svg(text):
    """The QR code of a text as an SVG document (bytes)."""
    buffer = BytesIO()
    # make_qr: never a Micro QR code; a pinned error correction level, so a
    # segno release cannot change the codes.
    segno.make_qr(text, error="m").save(buffer, kind="svg")
    return buffer.getvalue()


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
