import logging
import base64
import re
from io import BytesIO
from collections import namedtuple

from collections.abc import Generator
from contextlib import contextmanager
from django.db.transaction import atomic

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import format_html

from PIL import Image

from ..models import Device, Record


logger = logging.getLogger(__name__)


def get_device(EDV_ID=None, SAP_ID=None):
    # print('[get_device]: EDV_ID {EDV_ID}, SAP_ID {SAP_ID}'.format(
    #     EDV_ID=EDV_ID,
    #     SAP_ID=SAP_ID,
    # ))

    _message = ''
    _device = None
    _identifier = ''

    if SAP_ID and EDV_ID:
        _identifier = 'BOTH'

    # Check if EDV_ID and SAP_ID describe the same device:
    if _identifier == 'BOTH':
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
    username = str(user) if user else ''
    return user_obj(user, username)


def get_current_room_href(obj):
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
            filter=urlencode({"active_record__room__id__exact": f"{current_room.pk}"})
        )
        current_room_link = format_html('<a href="{}">{}</a>', url, current_room)

    return current_room_link


def save_base64img_as_fileimg(*, base64string, to_filepath, thumbnail_size):
    try:
        image_string = re.sub('^data:.+;base64,', '', base64string)

        with Image.open(BytesIO(base64.urlsafe_b64decode(image_string))) as img:
            img.load()
            img.thumbnail(thumbnail_size)
            img = img.convert('RGB')
            img.save(to_filepath, "JPEG")
    except BaseException as e:
        raise e


def get_has_note_badge(*, obj_type, level, has_note):
    if obj_type not in ["device", "record"]:
        raise NotImplementedError

    type_icon = ""
    note_icon = "fa-solid fa-comment" if has_note else "fa-solid fa-xmark"

    if obj_type == "record":
        type_icon = settings.THEME["RECORD"]["ICON"]
    elif obj_type == "device":
        type_icon = settings.THEME["DEVICE"]["ICON"]

    return format_html(
        '<span title="Record Notes exists" class="ml-2 p-1 badge badge-{level}"><i class="mr-2 fa-lg {type_icon}"></i><i class="fa-lg {note_icon}"></i></span>',
        type_icon=type_icon,
        note_icon=note_icon,
        level=level,
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
