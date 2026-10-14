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

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied, SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.views.decorators.http import last_modified, require_safe

from .. import lifecycle
from ..utils.htmx import missing_permission_message

# The directories directly under MEDIA_ROOT, each with the permissions of the
# screens that link its files; any one of them suffices, none means any
# logged-in user. Other directories are refused. A test checks the keys against
# the upload directories of all FileFields.
MEDIA_PERMISSIONS = {
    "attachments": ("core.view_record", "core.view_attachment"),
    "branding": (),  # logos on every printout
    "imported_csv": ("dataexchange.view_importerlist",),
    "links": (),  # public, see PUBLIC_MEDIA_DIRECTORY
    "reporting": ("reporting.view_report",),
    "rooms_reconcile": ("core.view_roomreconcile",),
    "sap_csv": ("inventory.view_saplist",),
    "toremove_csv": ("dataexchange.view_removerlist",),
    # Persons list and detail, device contact person, lending and smallstuff.
    settings.PERSON_IMAGE_UPLOAD_DIR: (
        "core.view_person",
        "core.view_device",
        "core.change_device",
        lifecycle.BY_NAME["lend"].permission,
        "smallstuff.view_assignedthing",
    ),
    settings.QRCODE_DIR: ("core.view_device", "core.view_room", "core.can_inventorize"),
    settings.SAP_LIST_COMPARISON_RESULT_FOLDER: ("core.change_inventory",),
}

# Directories whose files belong to tenant-owned objects, with their owners as
# (model, file lookup, tenant lookup). Such a file is served only when the
# user sees one of its owners' tenants, otherwise it is a 404 like the owner's
# own pages. A file no such object references (a room's QR code, an attachment
# on no record) needs only the permission; an owner without tenant still owns
# its file, as tenant scoping never includes objects without tenant.
MEDIA_TENANT_OWNERS = {
    settings.QRCODE_DIR: [("core.Device", "qrcode", "tenant")],
    "attachments": [("core.Record", "attachments__file", "device__tenant")],
    "imported_csv": [("dataexchange.ImporterList", "file", "tenant")],
}

# Public: the lent sheet prints these regulation files' URLs for borrowers,
# who usually have no login.
PUBLIC_MEDIA_DIRECTORY = "links"

# Content a browser runs when the file is opened directly. An uploaded HTML or
# SVG file must not act in the app's origin: sandbox gives it an opaque origin
# without scripts, forms or navigation. Showing an SVG in an <img> (the QR
# codes) is not affected.
ACTIVE_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "image/svg+xml", "text/xml", "application/xml"}
ACTIVE_CONTENT_POLICY = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


def _media_path(request, path):
    """The storage name for a path the user may fetch; 404 or 403 otherwise."""
    directory = path.split("/", 1)[0]
    # Only canonical paths: "links/../person_images/x.jpg" must not pass as
    # links/. A NUL byte would make the file system calls raise ValueError.
    if posixpath.normpath(path) != path or "\x00" in path or directory not in MEDIA_PERMISSIONS:
        raise Http404
    permissions = MEDIA_PERMISSIONS[directory]
    if permissions and not any(request.user.has_perm(permission) for permission in permissions):
        raise PermissionDenied(missing_permission_message(*permissions))
    if not _visible_in_tenants(request, directory, path):
        raise Http404
    return path


def _visible_in_tenants(request, directory, name):
    owned = False
    for label, file_lookup, tenant_lookup in MEDIA_TENANT_OWNERS.get(directory, ()):
        # _base_manager: soft-deleted owners still own their files.
        owners = apps.get_model(label)._base_manager
        # One filter() call: the file lookup may cross a multi-valued relation
        # (Record.attachments), and the tenant condition must apply to the same row.
        if owners.filter(**{file_lookup: name, f"{tenant_lookup}__in": request.tenants}).exists():
            return True
        owned = owned or owners.filter(**{file_lookup: name}).exists()
    return not owned


def _modified_time(request, name):
    try:
        return default_storage.get_modified_time(name)
    except (OSError, SuspiciousFileOperation):
        return None


@require_safe
def media(request, path):
    # 404 and 403 come first: a refused user gets no 304 either.
    return _file_response(request, _media_path(request, path))


@last_modified(_modified_time)
def _file_response(request, name):
    try:
        file = default_storage.open(name, "rb")
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
