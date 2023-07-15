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
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import format_html

from PIL import Image


logger = logging.getLogger(__name__)


def get_device(EDV_ID=None, SAP_ID=None):
    # print('[get_device]: EDV_ID {EDV_ID}, SAP_ID {SAP_ID}'.format(
    #     EDV_ID=EDV_ID,
    #     SAP_ID=SAP_ID,
    # ))

    from ..models import Device

    _message = ""
    _device = None
    _identifier = ""

    if SAP_ID and EDV_ID:
        _identifier = "BOTH"

    # Check if EDV_ID and SAP_ID describe the same device:
    if _identifier == "BOTH":
        try:
            _device = Device.objects.get(edv_id=EDV_ID, sap_id=SAP_ID)
        except Device.DoesNotExist as error:
            logger.error(error)
            _message = '[E] [get_device] EDV_ID "{EDV_ID}" and SAP_ID "{SAP_ID}" does not match!'

    try:
        if EDV_ID and not SAP_ID:
            _device = Device.objects.get(edv_id=EDV_ID)
        elif SAP_ID and not EDV_ID:
            _device = Device.objects.get(edv_id=SAP_ID)
        # print("[get_device] device: ", _device)
    except Device.DoesNotExist as error:
        logger.error(error)
        # raise

    return (_device, _message)


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


def get_current_room_href(obj):
    from ..models import Record, Device

    # Currently not used, leftover from MoveDeviceAdmin
    current_room_link = None
    current_room = None

    if isinstance(obj, Device):
        # print(f"obj {obj} isinstance Device!")
        current_room = obj.active_record.room
    elif isinstance(obj, Record):
        # print(f"obj {obj} isinstance Record!")
        current_room = obj.room

    if current_room:
        url = "{base_url}?{filter}".format(
            base_url=reverse("admin:core_device_changelist"),
            filter=urlencode({"active_record__room__id__exact": f"{current_room.pk}"}),
        )
        current_room_link = format_html('<a href="{}">{}</a>', url, current_room)

    return current_room_link


def save_base64img_as_fileimg(*, base64string, to_filepath, thumbnail_size):
    try:
        image_string = re.sub("^data:.+;base64,", "", base64string)

        with Image.open(BytesIO(base64.urlsafe_b64decode(image_string))) as img:
            img.load()
            img.thumbnail(thumbnail_size)
            img = img.convert("RGB")
            img.save(to_filepath, "JPEG")
    except BaseException as e:
        raise e


def get_icon_for_class(class_name):
    icon = ""

    try:
        icon = settings.THEME[class_name]["ICON"]
    except KeyError:
        pass

    return icon


def get_has_note_badge(*, obj_type, has_note):
    # if obj_type not in ["device", "record", "room", "device_type", "lent_record"]:
    #     raise NotImplementedError

    level = "light"
    note_icon = "fa-regular fa-comment"
    text = "No notes"
    type_icon = None

    if has_note:
        note_icon = "fa-solid fa-comment"
        level = "warning"
        text = "Notes exists"
        type_icon = get_icon_for_class(obj_type)

    return format_html(
        (
            '<span title="{text}" class="ml-2 p-1 badge badge-{level}"><i class="mr-2 fa-lg {type_icon}"></i><i'
            ' class="fa-lg {note_icon}"></i></span>'
        ),
        type_icon=type_icon,
        note_icon=note_icon,
        level=level,
        text=text,
    )


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
