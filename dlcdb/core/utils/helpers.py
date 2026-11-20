# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import base64
import logging
import re
from collections import namedtuple
from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.transaction import atomic
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)


def get_denormalized_user(user):
    """
    Keeping a string representation of the last user, even when the
    corresponding user instance gets deleted.
    """
    user_obj = namedtuple("user", ["user", "username"])
    username = str(user) if user else ""
    return user_obj(user, username)


def get_user_email(user):
    """
    In some cases the users email address is stored, but some user instances
    do not have an email address attached.
    TODO: Get domain from Site instance when user has no email.
    """

    if user.email:
        email = user.email
    else:
        email = f"{user.username}@example.org"

    return email


def get_contact_email(tenant=None):
    """
    Responsible contact/IT email, resolved through a single fallback chain:

    1. ``tenant.contact_email`` (per-tenant responsible address)
    2. ``Branding.organization_it_dept_email`` (global IT dept address)
    3. ``settings.DEFAULT_FROM_EMAIL`` (last-resort safety net)

    Shared resolver so notification routing, email footers etc. all agree on
    which address to use.
    """
    # Local import to avoid a circular import (organization.models -> core).
    from dlcdb.organization.models import Branding

    # `or` short-circuits, so Branding is only loaded when no tenant address.
    return (
        (tenant.contact_email if tenant else "")
        or Branding.load().organization_it_dept_email
        or settings.DEFAULT_FROM_EMAIL
    )


# Person photos, uploaded or from the HR sync, are stored as JPEGs of at most this size.
PERSON_PHOTO_SIZE = (400, 300)


def shrink_photo(source):
    """
    The image in the file object ``source`` as JPEG bytes of at most
    ``PERSON_PHOTO_SIZE``, turned upright. No metadata is copied: a phone
    photo's EXIF data, its GPS position for one, is dropped.
    """
    with Image.open(source) as img:
        # A JPEG then decodes at a fraction of its size, still at least as large
        # as needed whichever way it turns; other formats ignore it.
        side = max(PERSON_PHOTO_SIZE)
        img.draft("RGB", (side, side))
        upright = ImageOps.exif_transpose(img)
        upright.thumbnail(PERSON_PHOTO_SIZE)
        output = BytesIO()
        upright.convert("RGB").save(output, "JPEG")
    return output.getvalue()


def delete_photo_file(name):
    """
    Delete the stored person photo ``name`` once the transaction commits, unless
    a person still has it. Django deletes no files: a replaced or cleared photo
    would stay on disk, personal data nobody sees any more. After commit, so a
    rolled-back change keeps its file.
    """
    if not name:
        return
    # Local import, like get_contact_email's: the models import this module.
    from dlcdb.core.models import Person

    def delete():
        if not Person.with_softdeleted_objects.filter(photo=name).exists():
            default_storage.delete(name)

    transaction.on_commit(delete)


def save_base64img_as_fileimg(*, base64string, to_filepath):
    try:
        image_string = re.sub("^data:.+;base64,", "", base64string)
        photo = shrink_photo(BytesIO(base64.urlsafe_b64decode(image_string)))
    except UnidentifiedImageError as unidentified_image_error:
        logger.warning(f"Unidentified Image Error for `{to_filepath}`: {unidentified_image_error}")
        return
    with open(to_filepath, "wb") as file:
        file.write(photo)


class DoRollback(Exception):
    """
    Dry-run mode
    https://adamj.eu/tech/2022/10/13/dry-run-mode-for-data-imports-in-django/
    """


@contextmanager
def rollback_atomic() -> Generator[None, None, None]:
    """
    Dry-run mode
    https://adamj.eu/tech/2022/10/13/dry-run-mode-for-data-imports-in-django/
    """
    try:
        with atomic():
            yield
            raise DoRollback()
    except DoRollback:
        pass
