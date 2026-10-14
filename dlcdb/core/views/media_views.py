# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The uploaded and generated files under ``MEDIA_ROOT``, served by Django in
every installation, so the login applies to them like to every page. The web
server must not serve ``MEDIA_ROOT`` itself.

``FileResponse`` hands the file to ``wsgi.file_wrapper`` (``sendfile`` in
mod_wsgi and gunicorn), so no ``X-Sendfile`` module is needed.
"""

import posixpath

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.views.decorators.http import last_modified, require_safe

# The directories directly under MEDIA_ROOT; anything else is refused. A test
# checks this against the upload directories of all FileFields.
MEDIA_DIRECTORIES = {
    "attachments",
    "branding",
    "imported_csv",
    "links",
    "reporting",
    "rooms_reconcile",
    "sap_csv",
    "toremove_csv",
    settings.PERSON_IMAGE_UPLOAD_DIR,
    settings.QRCODE_DIR,
    settings.SAP_LIST_COMPARISON_RESULT_FOLDER,
}

# Public: the lent sheet prints these regulation files' URLs for borrowers,
# who usually have no login.
PUBLIC_MEDIA_DIRECTORY = "links"

# Content a browser runs when the file is opened directly. An uploaded HTML or
# SVG file must not run script in the app's origin; showing an SVG in an <img>
# (the QR codes) is not affected.
ACTIVE_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "image/svg+xml", "text/xml", "application/xml"}
ACTIVE_CONTENT_POLICY = "default-src 'none'; style-src 'unsafe-inline'"


def _media_path(path):
    """The storage name for a requested path, or 404."""
    # Only canonical paths: "links/../person_images/x.jpg" must not pass as links/.
    if posixpath.normpath(path) != path or path.split("/", 1)[0] not in MEDIA_DIRECTORIES:
        raise Http404
    return path


def _modified_time(request, path):
    try:
        return default_storage.get_modified_time(_media_path(path))
    except (OSError, SuspiciousFileOperation):
        return None


@require_safe
@last_modified(_modified_time)
def media(request, path):
    try:
        file = default_storage.open(_media_path(path), "rb")
    except (OSError, SuspiciousFileOperation) as error:  # missing, a directory, outside MEDIA_ROOT
        raise Http404 from error

    response = FileResponse(file)
    # Browsers may keep it, but revalidate: QR codes and person images are
    # overwritten in place. Last-Modified makes that a cheap 304.
    response["Cache-Control"] = "private, no-cache"
    if response["Content-Type"].split(";")[0] in ACTIVE_CONTENT_TYPES:
        response["Content-Security-Policy"] = ACTIVE_CONTENT_POLICY
    return response


@login_not_required
def public_media(request, path):
    return media(request, f"{PUBLIC_MEDIA_DIRECTORY}/{path}")
