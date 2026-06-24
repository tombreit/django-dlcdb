# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Single source of truth for moving one device to a new room.

Both the django-admin bulk relocate action
(``dlcdb.core.views.relocate_views.DevicesRelocateView``) and the frontend
relocate view (via ``dlcdb.assets.move``) call ``relocate_device`` so the
record-type state machine cannot drift between them.
"""

from dataclasses import dataclass

from django.contrib import messages
from django.utils.translation import gettext as _

from ..models import InRoomRecord, Record


@dataclass
class RelocateResult:
    """Outcome of a relocation attempt, ready to surface as a Django message."""

    level: int  # one of django.contrib.messages levels
    message: str


def relocate_device(device, new_room, user):
    """
    Move ``device`` to ``new_room`` on behalf of ``user``:

    - active record is LENT      -> update the room on the existing LENT record
    - active record is REMOVED   -> skip (device should no longer be here)
    - already in ``new_room``    -> skip (nothing to do)
    - otherwise (INROOM/LOST/...) -> create a new InRoomRecord, which becomes the
      device's active record via ``Record.save()``.
    """
    active_record = device.active_record
    record_type = getattr(active_record, "record_type", None)

    if record_type == Record.LENT:
        active_record.room = new_room
        active_record.save()
        return RelocateResult(
            level=messages.WARNING,
            message=_(
                "Device “%(device)s” is currently lent — updated the room of its "
                "active lending to “%(room)s”. The lending was not ended."
            )
            % {"device": device, "room": new_room},
        )

    if record_type == Record.REMOVED:
        return RelocateResult(
            level=messages.WARNING,
            message=_("Device “%(device)s” is removed and was not relocated.") % {"device": device},
        )

    if active_record is not None and active_record.room_id == new_room.pk:
        return RelocateResult(
            level=messages.INFO,
            message=_("Device “%(device)s” is already in room “%(room)s”.") % {"device": device, "room": new_room},
        )

    # Records are append-only history, so always create a fresh InRoomRecord:
    # get_or_create would match an older record from a previous stay in this room
    # and silently skip the move.
    InRoomRecord.objects.create(
        device=device,
        room=new_room,
        user=user,
        username=user.username,
    )
    return RelocateResult(
        level=messages.SUCCESS,
        message=_("Device “%(device)s” moved to room “%(room)s”.") % {"device": device, "room": new_room},
    )
