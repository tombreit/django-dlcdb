"""
Legacy import command
"""

import csv
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dlcdb.core.models import Device, Room, Record


class Command(BaseCommand):

    def get_edv_type(self, prefix):
        """
        Takes the real legacy prefix from the CSV original data and tries to match
        it with the defined device types.
        :param prefix:
        :return:
        """

        prefix = prefix.rstrip()

        for elem in Device.TYPE_CHOICER.get_list():

            if prefix == elem['prefix']:
                return elem['value']

        raise Exception('Passed legacy prefix does not match with existing types: ' + prefix)

    def handle(self, *args, **options):
        # unsere csv-Exportdatei aus der Access-Datenbank, !UTF-8!
        accessdb_file = os.path.join(settings.BASE_DIR, 'accessdb.csv')

        with open(accessdb_file, newline='\r\n') as csv_file:

            with transaction.atomic():
                rows = csv.reader(csv_file, delimiter=";", quotechar='"')

                for row in rows:

                    if rows.line_num == 1:
                        continue

                    """
                    ROOM
                    Befülle Room-Tabelle, falls in der AccessDB.csv ein Raum vorhanden ist
                    """
                    if row[4] != '':
                        # Kurzschreibweise für den try-exept-Block
                        # Room.objects.get_or_create(number=row[4])

                        try:
                            room_obj = Room.objects.get(number=row[4])
                        except Room.DoesNotExist:
                            room_obj = Room(number=row[4])
                            room_obj.save()

                    """
                    DEVICE
                    Befülle die Device-Tabelle mit den Daten der accessdb.csv
                    get type from edv-nummer:
                    MON1523 -> Monitor
                    set is_legacy flag
                    """

                    # cleanup edv-nummer
                    edv_nummer = row[1].lower()
                    edv_nummer = re.sub('[^0-9a-zA-Z]+', '*', edv_nummer)
                    edv_prefix = " ".join(re.findall("[a-zA-Z]+", edv_nummer))

                    edv_type = self.get_edv_type(edv_prefix)

                    device_obj = Device(
                        type=edv_type,
                        edv_id=row[1],
                        sap_id=row[2],
                        serial_number=row[3],
                        # room=[4],
                        mac_address=row[5],
                        note="Bezeichner: " + row[8] + "\n" + "Bemerkung: " + row[6],
                        is_legacy=True,
                    )
                    device_obj.save()

                    """
                    RECORD
                    record anlegen: mit Device und Room
                    """
                    # Raum ist vorhanden, record.type -> aufgestellt
                    if row[4] != '':
                        record_obj = Record(
                            device=device_obj,
                            room=room_obj,
                            type=3,
                        )
                        record_obj.save()
