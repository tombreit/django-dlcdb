# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Moving one device to a new room: dispatch to the right lifecycle transition and
return a display message.

Both the django-admin bulk relocate action
(``dlcdb.core.views.relocate_views.DevicesRelocateView``) and the frontend
relocate view (``dlcdb.assets.views.relocate``) call ``relocate_device``, which
delegates the actual record writing to ``dlcdb.core.lifecycle`` so the two entry
points cannot drift.
"""

from dataclasses import dataclass

from django.contrib import messages
from django.utils.translation import gettext as _

from .. import lifecycle
from ..models import Record


@dataclass
class RelocateResult:
    """Outcome of a relocation attempt, ready to surface as a Django message."""

    level: int  # one of django.contrib.messages levels
    message: str


def relocate_device(device, new_room, user):
    """
    Move ``device`` to ``new_room`` on behalf of ``user``, dispatching to the
    right lifecycle transition for the device's current state and returning a
    ready-to-display message. This is orchestration + presentation; the record
    writing itself lives in ``dlcdb.core.lifecycle``.

    - LENT     -> ``relocate_lending`` (update the room in place; lending continues)
    - REMOVED  -> refuse (the device should no longer be located)
    - same room -> no-op
    - LOST     -> ``transition_find`` (the device turned up in a room again)
    - INROOM   -> ``transition_relocate`` (append a new room record)
    - no record / ORDERED -> ``transition_locate`` (first localisation)
    """
    state = lifecycle.state_of(device)
    active_record = device.active_record

    if state == Record.LENT:
        lifecycle.relocate_lending(active_record, room=new_room, user=user)
        return RelocateResult(
            level=messages.WARNING,
            message=_(
                "Device “%(device)s” is currently lent — updated the room of its "
                "active lending to “%(room)s”. The lending was not ended."
            )
            % {"device": device, "room": new_room},
        )

    if state == Record.REMOVED:
        return RelocateResult(
            level=messages.WARNING,
            message=_("Device “%(device)s” is removed and was not relocated.") % {"device": device},
        )

    if active_record is not None and active_record.room_id == new_room.pk:
        return RelocateResult(
            level=messages.INFO,
            message=_("Device “%(device)s” is already in room “%(room)s”.") % {"device": device, "room": new_room},
        )

    # Append a fresh localisation record, picking the transition that matches the
    # current state so the record history names what actually happened (a LOST
    # device turning up is a "find", a fresh device is a "locate").
    lifecycle.localise(device, room=new_room, user=user)

    return RelocateResult(
        level=messages.SUCCESS,
        message=_("Device “%(device)s” moved to room “%(room)s”.") % {"device": device, "room": new_room},
    )
