# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Legacy import command
"""

import pathlib

from django.core.management.base import BaseCommand

from dlcdb.core.utils.timer import Timer
from dlcdb.core.utils.bulk_management import import_data
from dlcdb.core.models.importer import ImporterList


class Command(BaseCommand):
    help = "Takes a CSV file with devices and status and imports them. Does not update existing devices."

    def add_arguments(self, parser):
        # Positional obligatory arguments
        parser.add_argument("csv_file", type=str)
        parser.add_argument(
            "--mode",
            choices=["dryrun", "write"],
            default="dryrun",
            help="Simulate what to do. Basically a validation run.",
        )

    def handle(self, *args, **options):
        csv_fileobj = pathlib.Path(options["csv_file"])
        write = True if options["mode"] == "write" else False
        print(f"write {write=}: {csv_fileobj=}")

        with open(csv_fileobj, "rb") as csv_fileobj_open, Timer(name="context manager"):
            import_data(
                csv_fileobj_open,
                importer_inst_pk=None,
                valid_col_headers=ImporterList.VALID_COL_HEADERS,
                write=write,
            )
