# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The QR code of a device or a room: an SVG encoding QRCODE_PREFIX, the infix of
its model (QRCODE_INFIXES) and its uuid. Printed labels carry it, the inventory
scanner reads it (``qr_inventorize.js``). It is rendered per request
(``core.views.qrcode_views``), never stored.
"""

from io import BytesIO

import segno
from django.conf import settings


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
