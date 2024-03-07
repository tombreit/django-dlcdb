# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.management.base import BaseCommand
from dlcdb.core.models import Device, Record
from dlcdb.core.models.inventory import Inventory


class Command(BaseCommand):
    help = "Fix devices which are inventorized to a note pk instead to the room pk."

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

        current_inventory = Inventory.objects.get(is_active=True)

        for device in Device.objects.all():
            if any(
                [
                    device.active_record.record_type == Record.LOST,
                    device.active_record.record_type == Record.REMOVED,
                ]
            ):
                # print(f"Is LOST or REMOVED record. Continue with next device.")
                continue

            device_room = device.active_record.room

            device_inventory_note = device.device_notes.filter(inventory=current_inventory).order_by("-pk").first()
            if device_inventory_note:
                print(80 * "#")
                print(f"DEVICE: {device=}, {device.edv_id=}, {device.sap_id=}")
                print(f"RECORD: {device.active_record.pk=}, {device.active_record.record_type=}")
                print(f"ROOM:   {device_room=}, {device_room.pk=}")
                print(f"NOTE:   {device_inventory_note.pk}, {device_inventory_note.text=}")

                if device_room.pk == device_inventory_note.pk:
                    print(
                        "Match! device_room.pk { device_room.pk } == device_inventory_note.pk { device_inventory_note.pk }"
                    )
