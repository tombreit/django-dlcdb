import sys
import csv
import pathlib
from shutil import copyfile
from django.core.management.base import BaseCommand

from ...models import Device
from  dlcdb.inventory.sap import get_match_for_sap_id


class Command(BaseCommand):
    """
    Takes a CSV file, marks (via new column IS_IT_ASSET) all items which are in this DLCDB instance
    and gives back a CSV file.
    """

    help = 'Takes a CSV file, marks all items which are in this DLCDB \
            instance and gives back a CSV file.'

    def add_arguments(self, parser):
        # Positional obligatory arguments
        parser.add_argument('csv_input_file', type=str)
        parser.add_argument('csv_output_file', type=str)

        # Named (optional) arguments
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite output file if already exists.',
        )

    def handle(self, *args, **options):
        # Check if output file already exists:
        csv_output_file = options['csv_output_file']
        csv_output_file_obj = pathlib.Path(csv_output_file)

        if csv_output_file_obj.exists() and not options["force"]:
            sys.exit(f"Output file {csv_output_file_obj} already exists! Try with --force. Exit.")

        csv_input_file = options['csv_input_file']
        csv_input_file_obj = pathlib.Path(csv_input_file)

        print(csv_input_file, type(csv_input_file))
        print(csv_output_file, type(csv_output_file))

        # Get all sap_ids from this running DLCDB instance
        device_sap_ids = list(Device.objects.values_list("sap_id", flat=True))
        device_sap_ids = list(filter(None, device_sap_ids))
        # print(device_sap_ids)

        with open(csv_input_file_obj, "r") as csvinfile, open(csv_output_file_obj, "w") as csvoutfile:
            reader = csv.DictReader(csvinfile)
            print(f"reader.fieldnames: {reader.fieldnames}")
            writer_fieldnames = reader.fieldnames.copy()
            writer_fieldnames.insert(0, "IS_IT_ASSET")
            print(f"writer_fieldnames: {writer_fieldnames}")

            writer = csv.DictWriter(csvoutfile, fieldnames=writer_fieldnames)
            writer.writeheader()

            for row in reader:
                # if _match_msg: 
                #     print(80 * "*")
                #     print(_match_msg)
                #     print(row['Anlage'], row['Anlagenbezeichnung'])

                row.update({
                    'IS_IT_ASSET': get_match_for_sap_id(device_sap_ids, row['Anlage'], row['Unternummer']),
                })

                # print(row)
                # print(type(row))

                writer.writerow(row)

            self.stdout.write(self.style.SUCCESS('Successfully generated file "%s"' % csv_output_file))