# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging
import base64
import re
from io import BytesIO
from collections import namedtuple
from collections.abc import Generator
from contextlib import contextmanager
from contextlib import suppress

from django.db.transaction import atomic
from django.conf import settings

from PIL import Image, UnidentifiedImageError


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


def save_base64img_as_fileimg(*, base64string, to_filepath, thumbnail_size):
    try:
        image_string = re.sub("^data:.+;base64,", "", base64string)

        with Image.open(BytesIO(base64.urlsafe_b64decode(image_string))) as img:
            img.load()
            img.thumbnail(thumbnail_size)
            img = img.convert("RGB")
            img.save(to_filepath, "JPEG")
    except UnidentifiedImageError as unidentified_image_error:
        logger.warning(f"Unidentified Image Error for `{to_filepath}`: {unidentified_image_error}")
    except BaseException as e:
        raise e


def get_icon_for_class(class_name):
    icon = ""

    try:
        icon = settings.THEME[class_name]["ICON"]
    except KeyError:
        pass

    return icon


class DoRollback(Exception):
    """
    Dry-run mode
    https://adamj.eu/tech/2022/10/13/dry-run-mode-for-data-imports-in-django/
    """

    pass


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


def get_superuser_list(listing: list, list_item: str, is_superuser: bool) -> list:
    """
    Adds or removes 'tenant' from a list based on is_superuser.
    """

    with suppress(ValueError):
        if is_superuser:
            if list_item not in listing:
                listing.append(list_item)
        else:
            listing.remove(list_item)

    return listing
