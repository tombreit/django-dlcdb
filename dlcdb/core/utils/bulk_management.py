"""
Importer für Device-Listen im CSV-Format
"""

import csv
import io
import codecs
import magic
import string
import logging
from collections import namedtuple

from datetime import datetime

from django.db.transaction import atomic
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.apps import apps

from ..models import Device, Room, Record
from .helpers import get_device, rollback_atomic


logger = logging.getLogger(__name__)


TRUE_VALUES = ("yes", "ja", "true", "1")


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


def set_fk(row, key):
    obj = None
    value = row[key]

    if value:
        model_class_name = string.capwords(key, sep="_").replace("_", "")
        ModelClass = apps.get_model(f"core.{model_class_name}")
        obj, created = ModelClass.objects.get_or_create(name=value)

    return obj


def import_data(fileobj, importer_inst_pk=None, write=False):
    from dlcdb.tenants.models import Tenant
    from ..models import InRoomRecord
    
    ImporterMessages = namedtuple("ImporterMessages", [
        "success_messages",
        "imported_devices_count",
        "processed_rows_count",
    ])
    success_messages = []
    imported_devices_count = 0
    processed_rows_count = 0

    if write:
        atomic_context = atomic()
    else:
        atomic_context = rollback_atomic()

    with atomic_context:
        try:
            csv.register_dialect('custom_dialect', skipinitialspace=True, delimiter=',')
            rows = csv.DictReader(
                codecs.iterdecode(fileobj, 'utf-8'),
                dialect='custom_dialect',
            )

            for idx, row in enumerate(rows, start=1):
                # Header row is not included in rows (it is in rows.fieldnames),
                # so we do not need to exclude the header row manually
                processed_rows_count = idx

                # CSV DictReader always returns an empty string. But at
                # database level we need a Null value like None to 
                # support our unique constraints for edv_id and sap_id.
                edv_id = row['EDV_ID'] if row['EDV_ID'] else None
                sap_id = row['SAP_ID'] if row['SAP_ID'] else None
                
                print("edv_id: ", edv_id)
                print("sap_id: ", sap_id)

                device_repr = f"{edv_id or ''} {sap_id or ''}"

                try:
                    tenant = Tenant.objects.get(name=row['TENANT'])
                except KeyError as tenant_key_error:
                    raise KeyError(
                        '[Row {}] Device: "{}" NOT imported: TENANT not available in import file! ({})'.format(idx, device_repr, tenant_key_error)
                    )
                except ObjectDoesNotExist as tenant_does_not_exists:
                    raise ObjectDoesNotExist(
                            '[Row {}] Device: "{}" NOT imported: TENANT "{}" does not exist! ({})'.format(idx, device_repr, row['TENANT'], tenant_does_not_exists)
                    )

                # DEVICE
                try:
                    purchase_date = row['PURCHASE_DATE'] if row['PURCHASE_DATE'] else None
                    # if row['WARRANTY_EXPIRATION_DATE'] != '':
                    warranty_expiration_date = row['WARRANTY_EXPIRATION_DATE'] if row['WARRANTY_EXPIRATION_DATE'] else None
                    # if row['MAINTENANCE_CONTRACT_EXPIRATION_DATE'] != '':
                    maintenance_contract_expiration_date = row['MAINTENANCE_CONTRACT_EXPIRATION_DATE'] if row['MAINTENANCE_CONTRACT_EXPIRATION_DATE'] else None
                except ValueError:
                    raise ValidationError('Date format of a date field not recognized for device: {} - {}'.format(row['SAP_ID'], row['EDV_ID']))

                # Booleans
                is_lentable = True if row['IS_LENTABLE'].lower() in TRUE_VALUES else False
                is_licence = True if row['IS_LICENCE'].lower() in TRUE_VALUES else False

                device_obj = Device(
                    is_imported=True,
                    imported_by_id=importer_inst_pk,

                    # these fields should be mappable without further processing:
                    username=row['USERNAME'].strip() if row['USERNAME'] else '',
                    book_value=row['BOOK_VALUE'],
                    serial_number=row['SERIAL_NUMBER'],
                    series=row['SERIES'],
                    cost_centre=row['COST_CENTRE'],
                    note=row['NOTE'],
                    mac_address=row['MAC_ADDRESS'],
                    extra_mac_addresses=row['EXTRA_MAC_ADDRESSES'],
                    nick_name=row['NICK_NAME'],
                    
                    # These fields need some pre-processing
                    edv_id=edv_id,
                    sap_id=sap_id,
                    tenant=tenant,

                    # FK fields
                    manufacturer=set_fk(row, 'MANUFACTURER'),
                    device_type=set_fk(row, 'DEVICE_TYPE'),
                    supplier=set_fk(row, 'SUPPLIER'),

                    # Boolean fields
                    is_lentable=is_lentable,
                    is_licence=is_licence,

                    # Date fields
                    purchase_date=purchase_date,
                    warranty_expiration_date=warranty_expiration_date,
                    maintenance_contract_expiration_date=maintenance_contract_expiration_date,
                )
                device_obj.save()
                
                imported_devices_count += 1

                # INROOMRECORD
                room_number = row.get('ROOM', None)
                if room_number:
                    room_obj, created = Room.objects.get_or_create(number=room_number)

                    record_obj, created = InRoomRecord.objects.get_or_create(
                        device=device_obj,
                        room=room_obj,
                        username=row['USERNAME'].strip() if row['USERNAME'] else '',
                    )

                    success_messages.append('[Row {}] Device: "{}" / Record: "{}" imported.'.format(idx, device_repr, record_obj.pk))


        except IntegrityError as integrity_error:
            raise IntegrityError(f"Device {device_repr}: {integrity_error}")
        except BaseException as base_exception:
            raise BaseException(f"Device {device_repr}: {base_exception}")
        else:
            # No exception case
            pass
        finally:
            # Regardless of exception thrown or not
            pass
        
    result = ImporterMessages(
        success_messages,
        f"Imported devices: {imported_devices_count}",
        f"Processed rows from CSV: {processed_rows_count}",
    )
    return result
