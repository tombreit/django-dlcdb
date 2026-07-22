# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The device lifecycle -- states, transitions, and the functions that perform them.

This module is the single source of truth for "what state is a device in, what may
happen next, and how does each change get written". Read it top to bottom and you
know the whole lifecycle.

It has three parts:

1. **States** (``STATES``) -- the five record types, each with its label and the
   proxy model that writes it. ``None`` is the implicit initial state (a device
   with no record yet).
2. **The transition table** (``TRANSITIONS``) -- named moves, each listing the
   states it may start from. "Which states may follow this one" is *derived* from
   this table (``transitions_from``), never written down a second time.
3. **The transition functions** (``transition_*``) -- one per table row, the only
   sanctioned way to append a record. They check the source state, then let the
   proxy model do the actual writing (the proxies already stamp ``record_type``,
   normalise their fields and validate entry).

The proxies are resolved lazily via ``apps.get_model`` so this module can be
imported by ``record.py`` (which imports *it*) without a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .utils.helpers import get_denormalized_user


# ── State keys ──────────────────────────────────────────────────────────────
# The literal strings stored in ``Record.record_type``. They are a frozen public
# contract: baked into the DB CheckConstraint and served verbatim by the API, so
# transitions may be reorganised freely but a key must never be renamed or dropped.
ORDERED = "ORDERED"
INROOM = "INROOM"
LENT = "LENT"
LOST = "LOST"
REMOVED = "REMOVED"


class IllegalTransition(ValidationError):
    """A device is not in a legal source state for the attempted transition.

    Subclasses ``ValidationError`` so existing form/admin error handling keeps
    working unchanged.
    """


@dataclass(frozen=True)
class State:
    key: str  # the value stored in Record.record_type
    label: str  # gettext_lazy
    proxy: str  # "core.InRoomRecord", resolved lazily via apps.get_model


STATES = {
    ORDERED: State(key=ORDERED, label=_("Ordered"), proxy="core.OrderedRecord"),
    INROOM: State(key=INROOM, label=_("In room"), proxy="core.InRoomRecord"),
    LENT: State(key=LENT, label=_("Lent"), proxy="core.LentRecord"),
    LOST: State(key=LOST, label=_("Not locatable"), proxy="core.LostRecord"),
    REMOVED: State(key=REMOVED, label=_("Removed"), proxy="core.RemovedRecord"),
}

# Derived once, so the choices list, the CheckConstraint and the proxy registry
# all read from the same declaration. record.py re-exports these.
RECORD_TYPE_LIST = [(s.key, s.label) for s in STATES.values()]
RECORD_TYPE_KEYS = [s.key for s in STATES.values()]


@dataclass(frozen=True)
class Transition:
    name: str  # "lend", "return_lending", ...
    sources: tuple  # legal source state keys; None == "device has no record yet"
    target: str  # a STATES key -- its proxy does the writing
    label: str  # gettext_lazy; the *action* ("Lend", "Move")
    offered: bool = True  # surfaced as a UI action button at all?
    not_offered_from: tuple = ()  # sources where it is legal but NOT surfaced as a button
    permission: str | None = None  # defaults to "core.add_<target proxy>"
    device_q: Q | None = None  # extra precondition on the Device itself


TRANSITIONS = (
    Transition(name="order", sources=(None,), target=ORDERED, label=_("Order"), offered=False),
    Transition(name="locate", sources=(None, ORDERED), target=INROOM, label=_("Locate")),
    Transition(name="relocate", sources=(INROOM,), target=INROOM, label=_("Move")),
    Transition(
        name="lend",
        sources=(INROOM,),
        target=LENT,
        label=_("Lend"),
        device_q=Q(is_lentable=True, is_licence=False),
    ),
    Transition(name="return_lending", sources=(LENT,), target=INROOM, label=_("Return")),
    Transition(name="lose", sources=(INROOM, LENT, LOST), target=LOST, label=_("Not locatable")),
    Transition(name="find", sources=(LOST,), target=INROOM, label=_("Found")),
    # A device can be decommissioned from any live state, and also straight away
    # (source None) -- the bulk remover imports bare devices that never got a
    # record. Removing a lent device (decommission while on loan) is legal but
    # only via the admin, and a record-less device only offers "locate" on the
    # frontend, so LENT and None are legal-but-not-offered.
    Transition(
        name="remove",
        sources=(None, INROOM, LENT, LOST, ORDERED),
        target=REMOVED,
        label=_("Remove"),
        not_offered_from=(None, LENT),
    ),
    Transition(name="restore", sources=(REMOVED,), target=LOST, label=_("Restore"), offered=False),
    Transition(name="recover", sources=(REMOVED,), target=INROOM, label=_("Recover"), offered=False),
)

BY_NAME = {t.name: t for t in TRANSITIONS}


# ── Query API ───────────────────────────────────────────────────────────────


def state_of(device):
    """Current state key, or None if the device has no record yet."""
    return device.active_record.record_type if device.active_record_id else None


def transitions_from(state):
    """The Transition objects that may start from ``state``."""
    return tuple(t for t in TRANSITIONS if state in t.sources)


def can_transition(from_state, to_state):
    """True if some transition leads from ``from_state`` to ``to_state``. A pure predicate."""
    return any(t.target == to_state for t in transitions_from(from_state))


def offered_transitions_from(state):
    """The transitions surfaced as UI action buttons from ``state``.

    A transition is offered when it is ``offered`` at all and ``state`` is not in
    its ``not_offered_from`` (e.g. ``remove`` is legal from LENT but not offered
    there -- a lent device is returned or lost, not removed, from the frontend).
    """
    return tuple(t for t in transitions_from(state) if t.offered and state not in t.not_offered_from)


def proxy_for(state):
    """The proxy model class that writes ``state``."""
    return apps.get_model(STATES[state].proxy)


def permission_for(transition):
    """The permission string guarding ``transition`` (explicit, or derived from the target proxy)."""
    if transition.permission:
        return transition.permission
    proxy = proxy_for(transition.target)
    return f"{proxy._meta.app_label}.add_{proxy._meta.model_name}"


def available(device, *, user=None, app_name=None):
    """The transitions offered to ``user`` on ``device`` right now.

    A transition is available when it is ``offered``, the user holds its
    permission, and the device satisfies its ``device_q`` precondition.
    """
    result = []
    for transition in offered_transitions_from(state_of(device)):
        if not (user and user.has_perm(permission_for(transition))):
            continue
        if transition.device_q is not None:
            model = apps.get_model("core.Device")
            if not model.objects.filter(pk=device.pk).filter(transition.device_q).exists():
                continue
        result.append(transition)
    return result


def devices_for(name):
    """Devices for which transition ``name`` is currently possible.

    The single definition of "which devices may do this", shared by pickers,
    dashboards and counts so they cannot disagree.
    """
    t = BY_NAME[name]
    Device = apps.get_model("core.Device")
    concrete_sources = [s for s in t.sources if s is not None]
    qs = Device.objects.filter(active_record__record_type__in=concrete_sources)
    if None in t.sources:
        qs = qs | Device.objects.filter(active_record__isnull=True)
    return qs.filter(t.device_q) if t.device_q is not None else qs


# ── Enforcement ─────────────────────────────────────────────────────────────


def check(device, name):
    """Front-door guard: is transition ``name`` legal for ``device`` right now?

    Raises IllegalTransition otherwise. Stricter than the ``Record.save()``
    backstop, which only knows the resulting record_type, not which transition
    produced it.
    """
    transition = BY_NAME[name]
    current = state_of(device)
    if current not in transition.sources:
        raise IllegalTransition(
            _("Cannot %(action)s a device whose state is %(state)s.")
            % {"action": name, "state": current or _("not yet recorded")}
        )


def _actor(user):
    """The ``user`` / ``username`` denormalisation pair every write needs."""
    denorm = get_denormalized_user(user)
    return {"user": denorm.user, "username": denorm.username}


# ── Transition functions (one per table row) ────────────────────────────────


def transition_order(device, *, user, date_of_purchase=None):
    """None -> ORDERED. A device has been ordered but not yet taken into service."""
    check(device, "order")
    OrderedRecord = apps.get_model("core.OrderedRecord")
    return OrderedRecord.objects.create(device=device, date_of_purchase=date_of_purchase, **_actor(user))


def transition_locate(device, *, room, user, inventory=None, note=""):
    """None/ORDERED -> INROOM. The device's first localisation in a room."""
    check(device, "locate")
    InRoomRecord = apps.get_model("core.InRoomRecord")
    return InRoomRecord.objects.create(device=device, room=room, inventory=inventory, note=note, **_actor(user))


def transition_relocate(device, *, room, user, inventory=None, note=""):
    """INROOM -> INROOM. Move a located device to another room (appends a new record)."""
    check(device, "relocate")
    InRoomRecord = apps.get_model("core.InRoomRecord")
    return InRoomRecord.objects.create(device=device, room=room, inventory=inventory, note=note, **_actor(user))


def transition_lend(
    device,
    *,
    person,
    room,
    lent_start_date,
    lent_desired_end_date,
    user,
    sync_lent_end_date=False,
    lent_note="",
    lent_reason="",
    lent_accessories="",
):
    """INROOM -> LENT. Lend the device to a person."""
    check(device, "lend")
    LentRecord = apps.get_model("core.LentRecord")
    return LentRecord.objects.create(
        device=device,
        person=person,
        room=room,
        lent_start_date=lent_start_date,
        lent_desired_end_date=lent_desired_end_date,
        sync_lent_end_date=sync_lent_end_date,
        lent_note=lent_note,
        lent_reason=lent_reason,
        lent_accessories=lent_accessories,
        **_actor(user),
    )


def transition_return_lending(record, *, user, lent_end_date):
    """LENT -> INROOM. End the lending and return the device to the auto-return room.

    Two records: the LENT record is stamped with the return date (an in-place edit,
    not a transition), then an InRoomRecord is appended in the auto-return room.
    """
    check(record.device, "return_lending")
    Room = apps.get_model("core.Room")
    InRoomRecord = apps.get_model("core.InRoomRecord")
    actor = _actor(user)
    with transaction.atomic():
        record.lent_end_date = lent_end_date
        record.user, record.username = actor["user"], actor["username"]
        record.save()
        return InRoomRecord.objects.create(
            device=record.device,
            room=Room.objects.get(is_auto_return_room=True),
            **actor,
        )


def localise(device, *, room, user, inventory=None, note=""):
    """Put ``device`` in ``room``, choosing the INROOM-targeting transition that
    matches its current state (locate / relocate / find / recover).

    A convenience over the four transitions for callers that just want "this
    device is in this room now" regardless of where it came from -- the relocate
    dispatcher and the inventory found/unknown actions. Not a transition itself,
    so it carries no ``transition_`` prefix.
    """
    state = state_of(device)
    if state == INROOM:
        return transition_relocate(device, room=room, user=user, inventory=inventory, note=note)
    if state == LENT:
        # A lent device found in a room: move the lending there, keep it lent.
        return relocate_lending(device.active_record, room=room, user=user, inventory=inventory)
    if state == LOST:
        return transition_find(device, room=room, user=user, inventory=inventory, note=note)
    if state == REMOVED:
        return transition_recover(device, room=room, user=user, inventory=inventory, note=note)
    return transition_locate(device, room=room, user=user, inventory=inventory, note=note)


def transition_lose(device, *, user, inventory=None, note=""):
    """INROOM/LENT/LOST -> LOST. The device could not be located."""
    check(device, "lose")
    LostRecord = apps.get_model("core.LostRecord")
    return LostRecord.objects.create(device=device, inventory=inventory, note=note, **_actor(user))


def transition_find(device, *, room, user, inventory=None, note=""):
    """LOST -> INROOM. The device turned up again (typically during an inventory)."""
    check(device, "find")
    InRoomRecord = apps.get_model("core.InRoomRecord")
    return InRoomRecord.objects.create(device=device, room=room, inventory=inventory, note=note, **_actor(user))


def transition_remove(device, *, user, disposition_state="", removed_info="", note="", removed_date=None):
    """INROOM/LOST/ORDERED -> REMOVED. Decommission the device (sold, scrapped, ...)."""
    check(device, "remove")
    RemovedRecord = apps.get_model("core.RemovedRecord")
    return RemovedRecord.objects.create(
        device=device,
        disposition_state=disposition_state,
        removed_info=removed_info,
        removed_date=removed_date,
        note=note,
        **_actor(user),
    )


def transition_restore(device, *, user, note=""):
    """REMOVED -> LOST. Undo a decommission; LOST is the lowest-attribute state to
    park the device in until the operator sets its real state. Superuser-only."""
    check(device, "restore")
    LostRecord = apps.get_model("core.LostRecord")
    return LostRecord.objects.create(device=device, note=note, **_actor(user))


def transition_recover(device, *, room, user, inventory=None, note=""):
    """REMOVED -> INROOM. A decommissioned device was found during an inventory."""
    check(device, "recover")
    InRoomRecord = apps.get_model("core.InRoomRecord")
    return InRoomRecord.objects.create(device=device, room=room, inventory=inventory, note=note, **_actor(user))


# ── In-place moves (deliberately NOT transitions) ───────────────────────────
# These edit an existing active record instead of appending one, so no state
# change occurs and enforcement (which fires only on insert) does not apply. They
# live here, without the ``transition_`` prefix, so the distinction is visible.


def relocate_lending(record, *, room, user, inventory=None):
    """Move a *lent* device: update the room on the active LentRecord in place.

    The lending continues and no record is appended. Optionally stamps the
    current inventory (used when a lent device is found during stocktaking).
    """
    actor = _actor(user)
    record.room = room
    if inventory is not None:
        record.inventory = inventory
    record.user, record.username = actor["user"], actor["username"]
    record.save()
    return record
