import logging
from collections import namedtuple
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import format_html

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
