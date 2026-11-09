# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

r"""
Batch rename of rooms: one regular expression rewrites the room numbers.

Made for a change of numbering scheme, such as adding the building to bare
numbers: ``^(\d+)$`` → ``G\1`` turns 235 into G235. ``plan_renames`` is the
preview; ``apply_renames`` computes the plan again and saves it, so a stale
preview never decides what is saved.

A new number must be free, as on the add page (``theme.similar``): no other
room, deactivated ones included, may have it in another spelling. That holds
for a room renamed away in the same batch too: swaps and chains are refused.
"""

import re
from collections import Counter
from dataclasses import dataclass

from django.db import transaction
from django.utils.translation import gettext as _

from dlcdb.core.models import Room
from dlcdb.journal.models import JournalEntry
from dlcdb.theme.similar import comparable_name

JOURNAL_SOURCE = "rooms.rename"


@dataclass(frozen=True)
class Rename:
    """A room whose number the expression changes."""

    room: Room
    old_number: str
    new_number: str
    # Why the room keeps its number; empty when it is renamed.
    problem: str = ""


def plan_renames(pattern, replacement):
    """
    A ``Rename`` for every active room whose number the pattern matches and
    ``re.sub(pattern, replacement, number)`` changes, by number.

    An invalid expression raises ``re.error``, an unknown group name
    ``IndexError``; ``RoomRenameForm`` checks for both.
    """
    regex = re.compile(pattern)
    changed = []
    for room in Room.objects.order_by("number"):
        # Rooms the pattern does not match are not touched, not even trimmed.
        if not regex.search(room.number):
            continue
        new_number = regex.sub(replacement, room.number).strip()
        if new_number != room.number:
            changed.append((room, new_number))

    holders = {}
    for room in Room.with_softdeleted_objects.all():
        holders.setdefault(comparable_name(room.number), []).append(room)
    targets = Counter(comparable_name(new_number) for _room, new_number in changed)

    return [
        Rename(room, room.number, new_number, _problem(room, new_number, holders, targets))
        for room, new_number in changed
    ]


def _problem(room, new_number, holders, targets):
    """Why ``room`` cannot get ``new_number``, or an empty string."""
    max_length = Room._meta.get_field("number").max_length
    if not new_number:
        return _("The new number is empty.")
    if len(new_number) > max_length:
        return _("The new number is longer than %(max_length)d characters.") % {"max_length": max_length}

    key = comparable_name(new_number)
    others = [holder for holder in holders.get(key, []) if holder.pk != room.pk]
    if others:
        holder = others[0]
        if holder.deleted_at is not None:
            message = _("%(model)s “%(name)s” exists, but is deactivated.")
        else:
            message = _("%(model)s “%(name)s” already exists.")
        return message % {"model": Room._meta.verbose_name, "name": holder}
    if targets[key] > 1:
        return _("Another room gets the same number.")
    return ""


def apply_renames(pattern, replacement, *, user):
    """
    Rename the rooms of ``plan_renames`` that have no problem, in one
    transaction, and journal the batch as one entry. Returns the plan.
    """
    renames = plan_renames(pattern, replacement)
    applied = [rename for rename in renames if not rename.problem]
    if not applied:
        return renames

    with transaction.atomic():
        for rename in applied:
            rename.room.number = rename.new_number
            rename.room.stamp_user(user)
            rename.room.save()

        # Journal text is data, in English, like the other journal entries.
        lines = [f"Pattern: {pattern}", f"Replacement: {replacement}", ""]
        lines += [f"{rename.old_number} → {rename.new_number}" for rename in applied]
        skipped = [rename for rename in renames if rename.problem]
        if skipped:
            lines += ["", "Kept their number:"]
            lines += [f"{rename.old_number} (not {rename.new_number})" for rename in skipped]
        JournalEntry.objects.log(
            source=JOURNAL_SOURCE,
            event="renamed",
            summary=f"{len(applied)} room{'s' if len(applied) != 1 else ''} renamed",
            body="\n".join(lines),
            user=user,
        )
    return renames
