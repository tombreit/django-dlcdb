# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.management.base import BaseCommand, CommandError

from dlcdb.dataexchange.udb_sync import import_udb_persons


class Command(BaseCommand):
    help = "Import persons from an UDB instance."

    def handle(self, *args, **kwargs):
        try:
            report = import_udb_persons()
        except Exception as exc:
            # Detailed diagnostics are already logged by import_udb_persons();
            # surface a clean non-zero exit instead of a raw traceback.
            raise CommandError(f"UDB person import failed: {exc}") from exc

        if report is None:
            self.stdout.write("UDB sync is disabled (UdbSyncConfiguration.enabled is False).")
        else:
            self.stdout.write(report.detailed())
