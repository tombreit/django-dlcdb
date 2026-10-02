# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
A person's lendings and licence assignments, one entry each.

One assignment is often stored as several records: inventories used to stamp a
device by copying its active record, and ``fix_inventory_lost_lendings``
re-appended copies too. Copies share their device and their lending start (a
licence assignment has none). The first copy tells when the assignment began,
the latest one how it ended: return date, active flag, end of validity.
"""

from dataclasses import dataclass

from django.utils.timezone import localdate

from dlcdb.core.models import Record


@dataclass
class Assignment:
    """One lending or licence assignment, however many records store it."""

    first: Record
    latest: Record

    @property
    def began(self):
        """The lending start; a licence assignment, which has none, began with its first record."""
        return self.first.lent_start_date or localdate(self.first.created_at)

    @property
    def ended(self):
        """The return date, else the end of the latest record's validity; None while current."""
        if self.latest.lent_end_date:
            return self.latest.lent_end_date
        return localdate(self.latest.effective_until) if self.latest.effective_until else None


def group_assignments(records):
    """
    Group ``records`` into assignments: copies share their device and lending
    start. Current assignments first, then the most recently begun.
    """
    assignments = {}
    for record in records.order_by("pk"):
        key = (record.device_id, record.lent_start_date)
        if key in assignments:
            assignments[key].latest = record
        else:
            assignments[key] = Assignment(first=record, latest=record)
    return sorted(
        assignments.values(),
        key=lambda assignment: (assignment.latest.is_active, assignment.began),
        reverse=True,
    )
