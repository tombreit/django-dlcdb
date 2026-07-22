# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Audit the record history of every device against the lifecycle transition table.

Read-only. Walks each device's records in chronological order and reports every
consecutive (from_state -> to_state) pair that ``dlcdb.core.lifecycle`` does not
allow. Run this against a copy of production **before** turning on write-time
enforcement, so the table is known to match reality.

    python manage.py audit_transitions            # report illegal pairs
"""

from collections import Counter

from django.core.management.base import BaseCommand

from dlcdb.core import lifecycle
from dlcdb.core.models import Device, Record


class Command(BaseCommand):
    help = "Report device record chains that violate the lifecycle transition table."

    def handle(self, *args, **options):
        offenders = Counter()
        devices_with_issues = 0
        total = 0

        for device in Device.objects.all().iterator():
            records = Record.objects.filter(device=device).order_by("created_at", "pk")
            prev = None
            device_flagged = False
            for record in records:
                if prev is not None and not lifecycle.can_transition(prev, record.record_type):
                    offenders[(prev, record.record_type)] += 1
                    device_flagged = True
                    self.stdout.write(
                        f"device {device.pk} ({device}): {prev} -> {record.record_type} at record {record.pk}"
                    )
                prev = record.record_type
            total += 1
            if device_flagged:
                devices_with_issues += 1

        self.stdout.write("")
        self.stdout.write(f"Scanned {total} devices, {devices_with_issues} with at least one illegal pair.")
        if offenders:
            self.stdout.write("Illegal pairs by frequency:")
            for (frm, to), count in offenders.most_common():
                self.stdout.write(f"  {frm} -> {to}: {count}")
        else:
            self.stdout.write(self.style.SUCCESS("No illegal transitions found -- enforcement is safe to enable."))
