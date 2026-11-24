# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The QR code of a device or a room, rendered per request: an SVG encoding
QRCODE_PREFIX, the infix of its model (QRCODE_INFIXES) and its uuid. Printed
labels carry it, the inventory scanner reads it (``qr_inventorize.js``).

The image holds only what its URL holds, so the view neither looks the object
up nor checks its tenant: it reveals nothing and does not even confirm that
the object exists. The login applies as everywhere (LoginRequiredMiddleware).
"""

import segno
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_safe


@require_safe
def qrcode_svg(request, model_name, uuid):
    if model_name not in settings.QRCODE_INFIXES:
        raise Http404
    response = HttpResponse(content_type="image/svg+xml")
    # make_qr: never a Micro QR code; a pinned error correction level, so a
    # segno release cannot change the codes.
    text = f"{settings.QRCODE_PREFIX}{settings.QRCODE_INFIXES[model_name]}{uuid}"
    segno.make_qr(text, error="m").save(response, kind="svg")
    # The image of a URL never changes.
    response["Cache-Control"] = "private, max-age=31536000, immutable"
    return response
