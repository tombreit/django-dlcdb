# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The QR code of a device or a room, rendered per request.

The image holds only what its URL holds, so the view neither looks the object
up nor checks its tenant: it reveals nothing and does not even confirm that
the object exists. The login applies as everywhere (LoginRequiredMiddleware).
"""

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_safe

from ..utils import qrcode


@require_safe
def qrcode_svg(request, model_name, uuid):
    if model_name not in settings.QRCODE_INFIXES:
        raise Http404
    response = HttpResponse(qrcode.svg(qrcode.payload(model_name, uuid)), content_type="image/svg+xml")
    # The image of a URL never changes.
    response["Cache-Control"] = "private, max-age=31536000, immutable"
    return response
