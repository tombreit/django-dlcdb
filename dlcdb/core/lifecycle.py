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
   states it may start from and the permission that lets a user make the move.
   "Which states may follow this one" is *derived* from this table
   (``transitions_from``), never written down a second time.

   Note the two separate questions the table answers. *Legality* -- may this move
   happen at all -- is fixed here in ``sources``/``target`` and enforced on every
   write. *Offering* -- is this user invited to make it -- is deployment policy,
   so it lives in ``permission`` and is administered per group in the Django
   admin. Earlier versions hardcoded the offering as ``offered`` /
   ``not_offered_from`` flags; those are gone, and a transition no operator should
   see is now expressed by granting its permission to nobody.
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
    permission: str  # the permission that lets a user make this move; see Record.Meta
    device_precondition: Q | None = None  # a Q on Device that must hold for the transition


# Every row carries its own permission, declared in ``Record.Meta.permissions``.
# They are deliberately *not* derived from the target state's proxy model: five
# proxies cannot express ten distinct moves, and the collisions are exactly the
# ones that matter -- relocate, locate, find and recover all write an
# InRoomRecord, so "may move a device" and "may un-remove a device" would be the
# same grant. ``lend`` and ``return_lending`` do share a permission, because
# handing a device out and taking it back are one competence.
TRANSITIONS = (
    Transition(name="order", sources=(None,), target=ORDERED, label=_("Order"), permission="core.can_order_device"),
    Transition(
        name="locate", sources=(None, ORDERED), target=INROOM, label=_("Locate"), permission="core.can_locate_device"
    ),
    Transition(
        name="relocate", sources=(INROOM,), target=INROOM, label=_("Move"), permission="core.can_relocate_device"
    ),
    Transition(
        name="lend",
        sources=(INROOM,),
        target=LENT,
        label=_("Lend"),
        permission="core.can_lend_device",
        # Lendability is decided by is_lentable alone: a device flagged lentable
        # can be lent even if it is a licence.
        device_precondition=Q(is_lentable=True),
    ),
    Transition(
        name="return_lending",
        sources=(LENT,),
        target=INROOM,
        label=_("Return"),
        permission="core.can_lend_device",
    ),
    # Legal from LOST too, so an inventory can re-mark a device that is still missing.
    Transition(
        name="lose",
        sources=(INROOM, LENT, LOST),
        target=LOST,
        label=_("Not locatable"),
        permission="core.can_lose_device",
    ),
    Transition(name="find", sources=(LOST,), target=INROOM, label=_("Found"), permission="core.can_find_device"),
    # A device can be decommissioned from any live state, and also straight away
    # (source None) -- the bulk remover imports bare devices that never got a record.
    Transition(
        name="remove",
        sources=(None, INROOM, LENT, LOST, ORDERED),
        target=REMOVED,
        label=_("Remove"),
        permission="core.can_remove_device",
    ),
    # The two ways out of REMOVED. Their permissions ship granted to nobody, which
    # is what keeps a decommissioned device a dead end unless an operator decides
    # otherwise.
    Transition(
        name="restore", sources=(REMOVED,), target=LOST, label=_("Restore"), permission="core.can_restore_device"
    ),
    Transition(
        name="recover", sources=(REMOVED,), target=INROOM, label=_("Recover"), permission="core.can_recover_device"
    ),
)

BY_NAME = {t.name: t for t in TRANSITIONS}


# ── Localisation: the "put this device in a room" flow ──────────────────────
# The Move module (assets) and the admin bulk relocate both end with a device in
# a room, but they can get there by more than one move. Mapping each move to the
# states it starts from, once, is what lets the device picker, the view gate and
# ``core.utils.relocate.relocate_device`` agree instead of each restating which
# states it accepts -- a drift that used to produce buttons the view then refused.
#
# LENT rides along with ``relocate``: moving a lent device updates the room on
# its active lending in place (``relocate_lending``) and is not a transition at
# all, so it has no permission of its own.
#
# REMOVED is absent on purpose. Recovering a decommissioned device is a separate
# act with its own permission, offered from the admin rather than folded into a
# bulk mover.
LOCALISING_MOVES = {
    "locate": (None, ORDERED),
    "relocate": (INROOM, LENT),
    "find": (LOST,),
}

# The states ``relocate_device`` accepts; everything else it refuses.
RELOCATABLE_STATES = tuple({state for sources in LOCALISING_MOVES.values() for state in sources})


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


def proxy_for(state):
    """The proxy model class that writes ``state``."""
    return apps.get_model(STATES[state].proxy)


def permission_for(transition):
    """The permission string guarding ``transition``.

    Every row declares its own; nothing is derived. Kept as a function because it
    is the seam the UI and the tests go through.
    """
    return transition.permission


def localisable_states_for(user):
    """The source states from which ``user`` may put a device in a room.

    The union of the ``LOCALISING_MOVES`` entries whose permission the user
    holds, so a user who may only mark lost devices as found sees exactly the
    lost ones. An empty set means the user may make none of these moves; callers
    refuse access on that rather than rendering an empty picker.
    """
    states = set()
    for name, sources in LOCALISING_MOVES.items():
        if user and user.has_perm(BY_NAME[name].permission):
            states.update(sources)
    return states


def device_precondition_met(device, transition):
    """True if ``device`` satisfies the transition's ``device_precondition`` (or none is set)."""
    if transition.device_precondition is None:
        return True
    Device = apps.get_model("core.Device")
    return Device.objects.filter(pk=device.pk).filter(transition.device_precondition).exists()


def available(device, *, user=None):
    """The transitions offered to ``user`` on ``device`` right now.

    A transition is available when it is legal from the current state, the user
    holds its permission, and the device satisfies its ``device_precondition``.
    Those three conditions are the whole rule -- there is no separate notion of a
    move being legal but deliberately unsurfaced. This is the single gate for
    rendering transition actions in any UI (see ``core.utils.device_methods``).

    Note that a superuser passes every permission check, and so is offered every
    legal transition from the current state.
    """
    result = []
    for transition in transitions_from(state_of(device)):
        if not (user and user.has_perm(permission_for(transition))):
            continue
        if not device_precondition_met(device, transition):
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
    return qs.filter(t.device_precondition) if t.device_precondition is not None else qs


# ── Enforcement ─────────────────────────────────────────────────────────────


def check(device, name):
    """Front-door guard: is transition ``name`` legal for ``device`` right now?

    Checks both the source state and the transition's ``device_precondition``,
    and raises IllegalTransition otherwise. Stricter than the ``Record.save()``
    backstop, which only knows the resulting record_type, not which transition
    produced it.
    """
    transition = BY_NAME[name]
    current = state_of(device)
    if current not in transition.sources:
        raise IllegalTransition(
            _("“%(action)s” is not allowed for a device in state “%(state)s”.")
            % {"action": transition.label, "state": STATES[current].label if current else _("not yet recorded")}
        )
    if not device_precondition_met(device, transition):
        raise IllegalTransition(
            _("“%(action)s” is not allowed for device “%(device)s” in its current configuration.")
            % {"action": transition.label, "device": device}
        )


def check_state(device, target_state):
    """Backstop guard used by ``Record.save()`` on insert: is ``target_state`` a
    legal next state for ``device``?

    Weaker than ``check``: it only knows the resulting record_type, not which
    transition produced it (e.g. it cannot tell a ``find`` from a ``recover``).
    Raises IllegalTransition otherwise.
    """
    current = state_of(device)
    if not can_transition(current, target_state):
        raise IllegalTransition(
            _("Illegal state change for device %(device)s: %(current)s -> %(target)s.")
            % {"device": device, "current": current or _("no record"), "target": target_state}
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
    if record.record_type != LENT or not record.is_active:
        raise IllegalTransition(_("Only the active lending record of a device can be returned."))
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
    """Any state (including a device with no record yet) -> REMOVED. Decommission
    the device (sold, scrapped, ...)."""
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
    if record.record_type != LENT or not record.is_active:
        raise IllegalTransition(_("Only the active lending record of a device can be moved in place."))
    actor = _actor(user)
    record.room = room
    if inventory is not None:
        record.inventory = inventory
    record.user, record.username = actor["user"], actor["username"]
    record.save()
    return record
