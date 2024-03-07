# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.management.base import BaseCommand
from dlcdb.core.models import Device, Record
from dlcdb.core.models.inventory import Inventory


class Command(BaseCommand):
    help = "Fix LENT record which were erroneously transformed to a LOST record."

    def add_arguments(self, parser):
        # Positional obligatory arguments
        # parser.add_argument(
        #     'incident_date',
        #     type=str,
        #     help="Date the incident happended. Format: YYYY-MM-DD",
        # )

        # Named (optional) arguments
        parser.add_argument(
            "--doit",
            action="store_true",
            help="Do alter the database. The default (without this switch) is to only print what would be done by this command.",
        )

    def handle(self, *args, **options):
        """
        Condition:
        - Record has current inventory and record is LOST record
        - Record before was LENT Record
        """

        if options["doit"]:
            print(80 * "#")
            print("#")
            print("# Running with --doit turned on: Apply changes!")
            print("#")
            print(80 * "#")

        result = []
        current_inventory = Inventory.objects.get(is_active=True)

        for device in Device.objects.all():
            device_records = device.record_set.all().order_by("-created_at")

            if hasattr(device_records.first(), "record_type"):
                # https://docs.djangoproject.com/en/3.2/ref/models/instances/#django.db.models.Model.get_previous_by_FOO
                current_lost_record = device_records.first()
                try:
                    previous_record = device_records[1]
                except IndexError:
                    continue

                if all(
                    [
                        current_lost_record.record_type == Record.LOST,
                        current_lost_record.inventory == current_inventory,
                        previous_record.record_type == Record.LENT,
                    ]
                ):
                    print(80 * "~")
                    result.append(
                        f"Device '{device}', manufacturer '{device.manufacturer}', series '{device.series}', lender: '{previous_record.person}"
                    )

                    print(f"+ current_lost_record: {current_lost_record}, {current_lost_record.record_type}")
                    print(
                        f"+ previous_record:     {previous_record}, {previous_record.record_type}, {previous_record.person}"
                    )

                    print(80 * "-")
                    for dr in device_records:
                        print(f"# device record '{dr}', created_at '{dr.created_at}', type '{dr.record_type}'")

                    if options["doit"]:
                        new_record = previous_record
                        new_record.pk = new_record.id = None
                        new_record.user = None
                        new_record.username = "via management command fix_inventory_lost_lendings"
                        new_record._state.adding = True
                        new_record.save()

        print(80 * "=")
        for r in result:
            print(r)
        print(f"count: {len(result)}")
