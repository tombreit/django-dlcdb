"""
Import command für SAP-Daten der Verwaltung. 
"""

import csv
import argparse
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from dlcdb.core.models import Device, Room, Record, DeviceType


VERWALTUNG_DEVICE_TYPES = [
    'Tisch',
    'Stuhl',
    'Bett',
    'Drehstuhl',
    'Lampe',
    'Stehleuchte',
    'Schrank',
    'Regal',
    'Aktenvernichter',
    'Bücherwagen',
    'Container',
    'Bücher',
    'Zeitschriften',
    'Sonstiges',
]

VERWALTUNG_DEVICE_TYPES_ALIASES = {
    'Tisch': [],
    'Stuhl': ['Stühle', 'Stuehle'],
    'Drehstuhl': ['Drehstühle', 'Drehstuehle'],
    'Lampe/Stehleuchte': [],
    'Schrank': ['Schränke', 'Schraenke'],
    'Regal': [],
    'Aktenvernichter': [],
    'Bücherwagen': ['Buecherwagen', 'Bücherwägen', 'Buecherwaegen'],
    'Container': [],
    'Bücher/Zeitschriften': ['Buch', 'Buecher', 'Zeitschriften', 'Zeitschrift'],
    'Sonstiges': []
}



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--sapcsvfile', type=argparse.FileType('r'))

    def handle(self, *args, **options):
        # unsere csv-Exportdatei aus der Access-Datenbank, !UTF-8!
        accessdb_file = options['sapcsvfile']

        with open(accessdb_file) as csv_file:
            with transaction.atomic():
                mngmt_types = [DeviceType(name=n) for n in VERWALTUNG_DEVICE_TYPES]
                DeviceType.objects.bulk_create(mngmt_types)

                csv.register_dialect('custom_dialect', skipinitialspace=True, delimiter=',')
                rows = csv.DictReader(csv_file, dialect='custom_dialect')  # dialect=csv.excel_tab

                found_edv_ids = []

                for row in rows:

                    if rows.line_num == 1:
                        continue

                    print(f"{80 * '~'}")
                    print(f"row: {row}")

                    # ROOM
                    # Befülle Room-Tabelle, falls in der AccessDB.csv ein Raum vorhanden ist
                    room_obj = None
                    room_val = row['Raum']
                    if room_val != '':
                        # Kurzschreibweise für den try-exept-Block
                        # Room.objects.get_or_create(number=row[4])

                        try:
                            room_obj = Room.objects.get(number=room_val)
                        except Room.DoesNotExist:
                            room_obj = Room(number=room_val)
                            room_obj.save()

                    # DEVICE
                    # Befülle die Device-Tabelle mit den Daten der accessdb.csv
                    purchase_date = None
                    # print(datetime.strptime(row['Aktivdatum'], '%d.%m.%Y'))
                    try:
                        purchase_date = datetime.strptime(row['Aktivierung am'], '%d.%m.%Y')
                    except ValueError:
                        print('Ungültiger Datumswert: <', row['Aktivierung am'], '>')

                    sap_id = row['Anlage']
                    if row['Unternummer'] != '' and str(row['Unternummer']).isdigit() and int(row['Unternummer']) > 0:
                        sap_id += '-' + row['Unternummer']

                    edv_id = row['Anlagenbezeichnung']
                    found_edv_ids.append(edv_id)

                    if edv_id in found_edv_ids:
                        already_seen = found_edv_ids.count(edv_id)
                        edv_id = f"{edv_id}__{already_seen}"

                    # if row['Anlagenbezeichnung2']:
                    #     edv_id = '{} {}'.format(edv_id, row['Anlagenbezeichnung2'])

                    device_obj = Device(
                        edv_id=edv_id,
                        sap_id=sap_id,
                        purchase_date=purchase_date,
                        cost_centre=row['Kostenstelle'],
                        book_value=row['AnschWert'],
                        # book_value=row['Buchwert akt.'],
                        manufacturer=row['Hersteller der Anlage'],
                        serial_number=row['Serialnummer'],
                        series=row['Typenbezeichnung'],
                        note=row,
                    )
                    device_obj.save()

                    # RECORD
                    # record anlegen: mit Device und Room
                    # Raum ist vorhanden, record.type -> aufgestellt
                    if room_val != '' and room_obj:
                        record_obj = Record(
                            device=device_obj,
                            room=room_obj,
                            record_type=Record.INROOM,
                        )
                        record_obj.save()

                # This part tries to guess the device type by trying different aliases a name can contain
                for d_type in DeviceType.objects.all():
                    devices = Device.objects.filter(edv_id__icontains=d_type.name)
                    for alias in VERWALTUNG_DEVICE_TYPES_ALIASES.get(d_type.name, []):
                        devices = devices | Device.objects.filter(edv_id__icontains=alias)
                    devices.update(device_type=d_type)

                Device.objects.filter(device_type__isnull=True).update(device_type=DeviceType.objects.get(name='Sonstiges'))
