# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Repair ``Record.effective_until``: when each record was superseded.

A device's records form a chain. Appending a record supersedes the active one,
and ``Record.save()`` stamps it with ``effective_until``.

History, and the name: ``Record.save()`` used to close records by stamping
``modified_at`` on *every* record of the device at each append, which made
``modified_at`` useless as "superseded at". 305b5b9 (2022) introduced
``effective_until`` for it, moved the stamp there and added this command as the
backfill for records older than the column. The bulk stamping came along,
though, and re-stamped every earlier record on each append until 92e230c, so
older records claim to have stayed valid long after their successor took over.

The rule: a record is valid until the next record of its device (by id) is
created. A value is only rewritten when it is provably wrong:

  * empty on a superseded record: always filled (the original backfill);
  * over-stamped, i.e. later than the successor's ``created_at``: only with
    ``--repair-overstamped``. A record cannot stay valid after it was replaced.

Correct values are left exactly as they are: a live stamp is taken just before
its successor is written, and a value from the original backfill equals the
successor's creation.

Never touched: the active record, and every record of a device whose chain is
inconsistent (creation times out of id order, or not exactly one active record,
the latest). Those devices are listed instead.

Read-only unless ``--mode write``; all writes are one transaction.

    python manage.py fix_record_modified_at_timestamps --repair-overstamped                   # report
    python manage.py fix_record_modified_at_timestamps --repair-overstamped --device 6433 --mode write
    python manage.py fix_record_modified_at_timestamps --repair-overstamped --mode write
"""

from dataclasses import dataclass
from datetime import datetime
from itertools import groupby, pairwise
from operator import attrgetter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import localtime

from dlcdb.core.models import Record

EMPTY = "empty"
OVERSTAMPED = "over-stamped"


@dataclass(frozen=True)
class Repair:
    """One superseded record whose effective_until becomes its successor's creation."""

    record_pk: int
    device_pk: int
    old: datetime | None
    new: datetime
    reason: str


def _chain_problem(chain):
    """Why a device's record chain is too inconsistent to repair, or None."""
    created = [record.created_at for record in chain]
    if created != sorted(created):
        return "creation times are out of record order"
    active = [record for record in chain if record.is_active]
    if len(active) != 1 or active[0].pk != chain[-1].pk:
        return "the latest record is not the only active one"
    return None


def find_repairs(*, device_pk=None):
    """
    Every repair the rule allows, and the devices skipped as inconsistent, as
    ``(device_pk, reason)``. Read-only.
    """
    records = Record.objects.order_by("device_id", "pk").values_list(
        "pk", "device_id", "created_at", "effective_until", "is_active", named=True
    )
    if device_pk is not None:
        records = records.filter(device_id=device_pk)

    repairs, skipped = [], []
    for chain_device_pk, chain in groupby(records.iterator(), key=attrgetter("device_id")):
        chain = list(chain)
        if problem := _chain_problem(chain):
            skipped.append((chain_device_pk, problem))
            continue
        # The latest record is only ever a successor here, so it is never repaired.
        for record, successor in pairwise(chain):
            if record.effective_until is None:
                reason = EMPTY
            elif record.effective_until > successor.created_at:
                reason = OVERSTAMPED
            else:
                continue
            repairs.append(
                Repair(
                    record_pk=record.pk,
                    device_pk=chain_device_pk,
                    old=record.effective_until,
                    new=successor.created_at,
                    reason=reason,
                )
            )
    return repairs, skipped


def apply_repairs(repairs):
    """
    Write ``repairs`` in one transaction and return how many were written.

    ``update()`` writes the one column: no save() logic, and modified_at stays,
    since a repair is not an edit. A write only applies while the value is still
    the one found, so a record changed since the scan is left alone.
    """
    written = 0
    with transaction.atomic():
        for repair in repairs:
            written += Record.objects.filter(pk=repair.record_pk, effective_until=repair.old).update(
                effective_until=repair.new
            )
    return written


def _format(value):
    return "—" if value is None else f"{localtime(value):%Y-%m-%d %H:%M:%S}"


class Command(BaseCommand):
    help = "Repair Record.effective_until from the creation of each record's successor. Read-only unless --mode write."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["dryrun", "write"],
            default="dryrun",
            help="dryrun (default) only reports; write applies the repairs.",
        )
        parser.add_argument(
            "--repair-overstamped",
            action="store_true",
            help="Also repair over-stamped values (later than the successor's creation), not only empty ones.",
        )
        parser.add_argument(
            "--device",
            type=int,
            help="Limit to one device (its pk).",
        )

    def handle(self, *args, **options):
        device_pk = options["device"]
        if device_pk is not None and not Record.objects.filter(device_id=device_pk).exists():
            raise CommandError(f"Device {device_pk} has no records.")

        repairs, skipped = find_repairs(device_pk=device_pk)
        empty = [repair for repair in repairs if repair.reason == EMPTY]
        overstamped = [repair for repair in repairs if repair.reason == OVERSTAMPED]
        if not options["repair_overstamped"]:
            repairs = empty

        for skipped_device_pk, problem in skipped:
            self.stdout.write(self.style.WARNING(f"skipped device {skipped_device_pk}: {problem}"))
        if options["verbosity"] >= 2:
            for repair in repairs:
                self.stdout.write(
                    f"record {repair.record_pk} (device {repair.device_pk}): "
                    f"{_format(repair.old)} -> {_format(repair.new)}"
                )

        self.stdout.write(
            f"{len(skipped)} device(s) skipped, {len(empty)} empty value(s), "
            f"{len(overstamped)} over-stamped value(s) (later than their successor)."
        )
        if overstamped and not options["repair_overstamped"]:
            self.stdout.write("Add --repair-overstamped to repair them.")

        if options["mode"] != "write":
            self.stdout.write(self.style.WARNING(f"Dry run, nothing written: {len(repairs)} record(s) would change."))
            return

        written = apply_repairs(repairs)
        self.stdout.write(self.style.SUCCESS(f"{written} record(s) written."))
