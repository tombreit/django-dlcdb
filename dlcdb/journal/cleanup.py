# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Journal cleanup: remove entries that only repeat others, and old entries.

Status-like entries repeat while a condition persists: an HR sync run that
fails on the same contracts every 10 minutes, a logged error once per hour.
Of each group of identical entries only the first and the most recent are
kept: when the condition was first seen and that it was still going on.
Events that each happened (imports, mails, admin actions) are never touched.

Every cleanup leaves one journal entry about itself.
"""

import calendar
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from .models import JournalEntry

HR_SYNC_SOURCE = "dataexchange.hr_sync"
ANOMALY_EVENTS = ("log", "exception")

# The row number shifts when HR adds or drops a person; the row itself does not.
_ROW_PREFIX = re.compile(r"^\[row \d+\] ")

# SQLite limits the number of query parameters; delete in chunks below it.
_CHUNK = 500


def _entries(count):
    return f"{count} {'entry' if count == 1 else 'entries'}"


@dataclass
class RepeatGroup:
    """Identical entries: the first and the latest stay, the ones between go."""

    source: str
    event: str
    summary: str  # of the latest entry
    first: datetime
    latest: datetime
    removable: list = field(default_factory=list)  # pks


def _content_key(entry):
    if entry.source == HR_SYNC_SOURCE:
        # The header (with its timestamp) and the counts line ("Unchanged: 256")
        # differ from run to run; the notable rows say what happened.
        rows = tuple(_ROW_PREFIX.sub("", line) for line in entry.body.splitlines() if line.startswith("[row "))
        return (entry.source, entry.event, entry.level, rows)
    return (entry.source, entry.event, entry.level, entry.summary, entry.body)


def repeat_groups():
    """
    The groups of repeated HR sync runs and anomalies that have something to
    remove. Both are tenant-less system entries, which every journal viewer sees.
    """
    candidates = (
        JournalEntry.objects.filter(Q(source=HR_SYNC_SOURCE) | Q(event__in=ANOMALY_EVENTS), tenant__isnull=True)
        .order_by("timestamp", "pk")
        .only("pk", "timestamp", "source", "event", "level", "summary", "body")
    )
    entries_by_key = defaultdict(list)
    for entry in candidates.iterator():
        entries_by_key[_content_key(entry)].append(entry)

    return [
        RepeatGroup(
            source=entries[-1].source,
            event=entries[-1].event,
            summary=entries[-1].summary,
            first=entries[0].timestamp,
            latest=entries[-1].timestamp,
            removable=[entry.pk for entry in entries[1:-1]],
        )
        for entries in entries_by_key.values()
        if len(entries) > 2
    ]


def months_before(moment, months):
    """The same day and time ``months`` calendar months earlier, or the last
    day of that month when it is shorter (March 31 → February 28/29)."""
    year, month_index = divmod(moment.year * 12 + moment.month - 1 - months, 12)
    month = month_index + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def remove(pks, *, user, event, summary, body=""):
    """Delete the entries ``pks`` and journal the cleanup itself. Returns the count."""
    pks = list(pks)
    for start in range(0, len(pks), _CHUNK):
        JournalEntry.objects.filter(pk__in=pks[start : start + _CHUNK]).delete()
    if pks:
        JournalEntry.objects.log(source="journal", event=event, summary=summary, body=body, user=user)
    return len(pks)


def remove_repeats(*, user):
    groups = repeat_groups()
    lines = [
        f"{group.source} {group.event}: {len(group.removable)} removed, "
        f"kept {timezone.localtime(group.first):%Y-%m-%d %H:%M} and {timezone.localtime(group.latest):%Y-%m-%d %H:%M} "
        f"({group.summary})"
        for group in groups
    ]
    count = sum(len(group.removable) for group in groups)
    return remove(
        (pk for group in groups for pk in group.removable),
        user=user,
        event="repeats_removed",
        summary=f"Removed {_entries(count)} (repeats)",
        body="\n".join(lines),
    )


def remove_older_than(entries, cutoff, *, user):
    """Delete those of ``entries`` (the caller's visible ones) from before ``cutoff``."""
    pks = list(entries.filter(timestamp__lt=cutoff).values_list("pk", flat=True))
    return remove(
        pks,
        user=user,
        event="old_entries_removed",
        summary=f"Removed {_entries(len(pks))} older than {timezone.localtime(cutoff):%Y-%m-%d}",
    )
