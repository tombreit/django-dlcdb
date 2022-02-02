"""
Importer für Device-Listen im CSV-Format
"""

import csv
import io
import codecs
import magic
import logging

from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from ..models import Device, Room, Record, DeviceType, Supplier
from .helpers import get_device


logger = logging.getLogger(__name__)


def validate_csv(csvfile, valid_col_headers=None, date_fields=None, bulk_mode=None):
    """
    Validate CSV file object.
    """
    print("[validate_csv] Processing CSV file:", csvfile)

    # Error dict, gets updated with the errors found
    error_list = []

    ALLOWED_CONTENT_TYPES = [
        'text/plain',
        'text/csv',
        'application/csv',
    ]

    # Validating file type
    csvfile.seek(0, 0)
    _content_type = magic.from_buffer(csvfile.read(), mime=True)
    _file_suffix = csvfile.path.lower()

    print(_content_type)

    if (_content_type not in ALLOWED_CONTENT_TYPES) or (not _file_suffix.endswith('csv')):
        raise ValidationError(
            'Datei scheint keine CSV-Datei zu sein. Got: content_type: "{}", suffix: "{}"'.format(
                _content_type,
                _file_suffix,
            )
        )

    csvfile.seek(0, 0)
    decoded_file = csvfile.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    # print(io_string.getvalue())

    csv.register_dialect('custom_dialect', skipinitialspace=True, delimiter=',')
    rows = csv.DictReader(
        io_string,
        dialect='custom_dialect',
    )

    # Validating column headers
    current_col_headers = set(rows.fieldnames)
    expected_col_headers = set(valid_col_headers)

    if not expected_col_headers.issubset(current_col_headers):

        missing_col_headers = expected_col_headers.difference(current_col_headers)
        error_list.append(ValidationError(
            'Erwartete Spaltenköpfe nicht in CSV-Datei gefunden [no subset]! Expected: "{}", got: "{}". Missing headers: "{}"'.format(
                expected_col_headers,
                current_col_headers,
                missing_col_headers,
            )
        ))

    for idx, row in enumerate(rows, start=1):

        # Validating items without EDV_ID or SAP_ID
        if (not row['EDV_ID']) and (not row['SAP_ID']):
            error_list.append(ValidationError(f'Item in row {idx} without EDV_ID and SAP_ID! Row raw data: {row}'))

        if bulk_mode == 'import_devices':
            # Validating clash with already existing Devices
            if row['EDV_ID'].strip() and Device.objects.filter(edv_id=row['EDV_ID']).exists():
                error_list.append(ValidationError('Device with this EDV_ID already exists: {}'.format(row['EDV_ID'])))

            if row['SAP_ID'].strip() and Device.objects.filter(sap_id=row['SAP_ID']).exists():
                error_list.append(ValidationError('Device with this SAP_ID already exists: {}'.format(row['SAP_ID'])))

        if date_fields:
            for key, value in row.items():
                # Validating date format for DateFields
                if key in date_fields:
                    # print(key, value)
                    if value != '':
                        try:
                            datetime.strptime(value, '%Y-%m-%d')
                        except ValueError:
                            error_list.append(ValidationError('Incorrect date format, should be YYYY-MM-DD: {}: {}'.format(key, value)))

    if error_list:
        raise ValidationError(error_list)


def set_removed_record(fileobj):
    """
    Mark a device as "removed".
    * Identify device given in CSV, via EDV_ID or SAP_ID or both
    * Search active record for given device
    * Create a new removed-record with attributes given in CSV
    """
    print('[set_removed_record]...')
    now = datetime.now()

    messages = []
    errors_count = 0
    removed_devices_count = 0
    processed_rows_count = 0

    messages.append('[I] Starting set_removed_record...')

    with transaction.atomic():
        csv.register_dialect('custom_dialect', skipinitialspace=True, delimiter=',')
        rows = csv.DictReader(
            codecs.iterdecode(fileobj, 'utf-8'),
            dialect='custom_dialect',
        )

        for idx, row in enumerate(rows, start=1):
            # header row is not included in rows (it is in rows.fieldnames),
            # so we do not need to exclude the header row manually

            processed_rows_count = idx

            EDV_ID = row['EDV_ID'].strip()
            SAP_ID = row['SAP_ID'].strip()

            # Check if we have either an EDV_ID, a SAP_ID or both
            device, _message = get_device(EDV_ID=EDV_ID, SAP_ID=SAP_ID)
            if not device:
                messages.append('[E][Row {}] Device not found: EDV_ID "{}", SAP_ID "{}"! Ignoring this device!'.format(idx, EDV_ID, SAP_ID))
                errors_count += 1
                continue

            # Check for other errors which may occured in get_device()
            if _message:
                messages.append(_message)
                errors_count += 1
                continue

            # Check if the current record for this device is already a 'removed' record
            _already_removed_record = Record.objects.filter(
                Q(is_active=True),
                Q(device=device),
                Q(record_type=Record.REMOVED),
            ).first()

            if _already_removed_record:
                messages.append('[I][Row {}] Device already "removed": EDV_ID "{}", SAP_ID "{}", Record PK: "{}". Ignoring this device.'.format(idx, EDV_ID, SAP_ID, _already_removed_record.pk))
                continue

            # Create new record for this device
            try:
                record, created = Record.objects.get_or_create(
                    device=device,
                    record_type=Record.REMOVED,
                    note=row['NOTE'],
                    username=row['USERNAME'].strip() if row['USERNAME'] else '',
                    disposition_state=row['DISPOSITION_STATE'],
                    removed_info=row['REMOVED_INFO'],
                    removed_date=row['REMOVED_DATE'] if row['REMOVED_DATE'] else now,
                )
                print("created: ", created)
                messages.append('[I][Row {}] Device {} - Record set to removed: {}.'.format(idx, device, record.pk))
                removed_devices_count += 1
            except Exception as ex:
                messages.append('[I][Row {}] "Something bad happend:-(. Please contact your administrator. Exception: "{}"'.format(idx, ex))
                raise

    messages.extend([
        "-------------------------------------------",
        'Processed rows from CSV: {}'.format(processed_rows_count),
        'Errors: {}'.format(errors_count),
        'Removed devices: {}'.format(removed_devices_count),
        "-------------------------------------------",
    ])
    return '\n'.join(messages)


def import_data(fileobj, importer_inst_pk=None):
    from dlcdb.tenants.models import Tenant
    from ..models import InRoomRecord
    
    messages = []
    imported_devices_count = 0
    processed_rows_count = 0
    errors = 0

    messages.append('[I] Starting import...')

    with transaction.atomic():
        csv.register_dialect('custom_dialect', skipinitialspace=True, delimiter=',')
        rows = csv.DictReader(
            codecs.iterdecode(fileobj, 'utf-8'),
            dialect='custom_dialect',
        )

        for idx, row in enumerate(rows, start=1):
            # header row is not included in rows (it is in rows.fieldnames),
            # so we do not need to exclude the header row manually

            processed_rows_count = idx

            edv_id = None
            if row['EDV_ID']:
                edv_id = row['EDV_ID']

            sap_id = None
            if row['SAP_ID']:
                sap_id = row['SAP_ID']

            try:
                tenant = Tenant.objects.get(name=row['TENANT'])
            except KeyError as e:
                errors += 1
                messages.append(
                    '[!][Row {}] Device: "{}" NOT imported: TENANT not available in import file!'.format(idx, edv_id)
                )
                continue
            except ObjectDoesNotExist:
                errors += 1
                messages.append(
                    '[!][Row {}] Device: "{}" NOT imported: TENANT "{}" does not exist!'.format(idx, edv_id, row['TENANT'])
                )
                continue

            """
            ROOM
            Befülle Room-Tabelle
            """
            room_obj = None
            room_val = row['ROOM']
            if room_val != '':
                room_obj, created = Room.objects.get_or_create(number=room_val)

            """
            SUPPLIER
            Befülle die Supplier-Tabelle
            """
            supplier_obj = None
            supplier_val = row['SUPPLIER']
            if supplier_val != '':
                supplier_obj, created = Supplier.objects.get_or_create(name=supplier_val)

            """
            DEVICETYPE
            """
            device_type_obj = None
            device_type_val = row['DEVICE_TYPE']
            if device_type_val != '':
                device_type_obj, created = DeviceType.objects.get_or_create(name=device_type_val)

            """
            DEVICE
            Befülle die Device-Tabelle mit den Daten der csv-Datei
            """
            # purchase_date, warranty_expiration_date, maintenance_contract_expiration_date = 0, 0, 0
            try:
                purchase_date = row['PURCHASE_DATE'] if row['PURCHASE_DATE'] else None
                # if row['WARRANTY_EXPIRATION_DATE'] != '':
                warranty_expiration_date = row['WARRANTY_EXPIRATION_DATE'] if row['WARRANTY_EXPIRATION_DATE'] else None
                # if row['MAINTENANCE_CONTRACT_EXPIRATION_DATE'] != '':
                maintenance_contract_expiration_date = row['MAINTENANCE_CONTRACT_EXPIRATION_DATE'] if row['MAINTENANCE_CONTRACT_EXPIRATION_DATE'] else None
            except ValueError:
                raise ValidationError('Date format of a date field not recognized for device: {} - {}'.format(row['SAP_ID'], row['EDV_ID']))

            is_lentable = True if row['IS_LENTABLE'] == "True" else False

            is_licence = True if row['IS_LICENCE'] == "True" else False

            device_obj = Device(
                is_imported=True,
                imported_by_id=importer_inst_pk,
                # these fields should be mappable without further processing:
                edv_id=edv_id,
                username=row['USERNAME'].strip() if row['USERNAME'] else '',
                sap_id=sap_id,
                book_value=row['BOOK_VALUE'],
                serial_number=row['SERIAL_NUMBER'],
                manufacturer=row['MANUFACTURER'],
                series=row['SERIES'],
                cost_centre=row['COST_CENTRE'],
                note=row['NOTE'],
                mac_address=row['MAC_ADDRESS'],
                extra_mac_addresses=row['EXTRA_MAC_ADDRESSES'],
                nick_name=row['NICK_NAME'],
                # these fields need some pre-processing
                device_type=device_type_obj,
                is_lentable=is_lentable,
                is_licence=is_licence,
                supplier=supplier_obj,
                purchase_date=purchase_date,
                warranty_expiration_date=warranty_expiration_date,
                maintenance_contract_expiration_date=maintenance_contract_expiration_date,
                tenant=tenant,
            )
            device_obj.save()

            """
            INROOMRECORD
            """
            record_obj, created = InRoomRecord.objects.get_or_create(
                device=device_obj,
                room=room_obj,
                username=row['USERNAME'].strip() if row['USERNAME'] else '',
            )

            messages.append('[I][Row {}] Device: "{}" / Record: "{}" imported.'.format(idx, edv_id, record_obj.pk))
            imported_devices_count += 1

    # Hint: 'Imported devices: NNN' is used in importerlist_admin in a regex.
    messages.extend([
        "-------------------------------------------",
        'Processed rows from CSV: {}'.format(processed_rows_count),
        'Imported devices: {}'.format(imported_devices_count),
        "-------------------------------------------",
    ])

    return '\n'.join(messages)
