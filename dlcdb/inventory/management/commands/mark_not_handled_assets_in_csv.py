# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import csv
import pathlib
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from dlcdb.core.models import Device

from ...sap import get_match_for_sap_id


class Command(BaseCommand):
    """
    Takes a CSV file, marks (via new column IS_IT_ASSET) all items which are in this DLCDB instance
    and gives back a CSV file.
    """

    help = (
        "Takes a CSV file, marks all items which are in this DLCDB instance and gives back a CSV file. "
        "Use -v 2 to list every matched row."
    )

    def add_arguments(self, parser):
        # Positional obligatory arguments
        parser.add_argument("csv_input_file", type=str)
        parser.add_argument("csv_output_file", type=str)

        # Named (optional) arguments
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite output file if already exists.",
        )

    def handle(self, *args, **options):
        # Check if output file already exists:
        csv_output_file = options["csv_output_file"]
        csv_output_file_obj = pathlib.Path(csv_output_file)

        if csv_output_file_obj.exists() and not options["force"]:
            raise CommandError(f"Output file {csv_output_file_obj} already exists. Use --force to overwrite it.")

        csv_input_file = options["csv_input_file"]
        csv_input_file_obj = pathlib.Path(csv_input_file)

        # Get all sap_ids from this running DLCDB instance
        device_sap_ids = list(Device.objects.values_list("sap_id", flat=True))
        device_sap_ids = list(filter(None, device_sap_ids))
        self.stdout.write(f"Comparing {csv_input_file} with the {len(device_sap_ids)} SAP IDs of this DLCDB.")

        # Rows per match type, the first word of the match message: "exact",
        # "combined", "anlagenummeronly", or "0" for a row not in this DLCDB.
        matches = Counter()
        with open(csv_input_file_obj, "r") as csvinfile, open(csv_output_file_obj, "w") as csvoutfile:
            reader = csv.DictReader(csvinfile)
            writer_fieldnames = reader.fieldnames.copy()
            writer_fieldnames.insert(0, "IS_IT_ASSET")

            writer = csv.DictWriter(csvoutfile, fieldnames=writer_fieldnames)
            writer.writeheader()

            for row in reader:
                match = get_match_for_sap_id(device_sap_ids, row["Anlage"], row["Unternummer"])
                row.update({"IS_IT_ASSET": match})
                writer.writerow(row)

                match_type = match.split(" ", 1)[0]
                matches[match_type] += 1
                if match_type != "0" and options["verbosity"] >= 2:
                    description = row.get("Anlagenbezeichnung", "")
                    self.stdout.write(f"  {row['Anlage']}/{row['Unternummer']} {description}: {match}")

        rows = sum(matches.values())
        not_found = matches.pop("0", 0)
        by_type = ", ".join(f"{match_type}: {count}" for match_type, count in sorted(matches.items()))
        self.stdout.write(f"{rows} rows read. IT assets of this DLCDB: {rows - not_found} ({by_type or 'none'}).")
        self.stdout.write(f"Not in this DLCDB: {not_found} (IS_IT_ASSET is 0).")
        self.stdout.write(self.style.SUCCESS(f'Written to "{csv_output_file}", with IS_IT_ASSET as the first column.'))
