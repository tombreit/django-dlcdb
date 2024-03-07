# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Importer für Device-Listen im CSV-Format
"""

import csv
import io
from io import StringIO
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
from .helpers import rollback_atomic
from .sap_converter import convert_raw_sap_export


# https://docs.djangoproject.com/en/4.1/topics/db/instrumentation/
# from django.db import connection
# from .query_logger import QueryLogger
# ql = QueryLogger()
# with connection.execute_wrapper(ql):
#     do_queries()
# # Now we can print the log.
# print(ql.queries)


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
        "text/plain",
        "text/csv",
        "application/csv",
    ]

    # Validating file type
    csvfile.seek(0, 0)
    _content_type = magic.from_buffer(csvfile.read(), mime=True)
    _file_suffix = csvfile.path.lower()

    print(_content_type)

    if (_content_type not in ALLOWED_CONTENT_TYPES) or (not _file_suffix.endswith("csv")):
        raise ValidationError(
            'Datei scheint keine CSV-Datei zu sein. Got: content_type: "{}", suffix: "{}"'.format(
                _content_type,
                _file_suffix,
            )
        )

    csvfile.seek(0, 0)
    decoded_file = csvfile.read().decode("utf-8")
    io_string = io.StringIO(decoded_file)
    # print(io_string.getvalue())

    csv.register_dialect("custom_dialect", skipinitialspace=True, delimiter=",")
    rows = csv.DictReader(
        io_string,
        dialect="custom_dialect",
    )

    # Validating column headers
    current_col_headers = set(rows.fieldnames)
    expected_col_headers = set(valid_col_headers)

    if not expected_col_headers.issubset(current_col_headers):
        missing_col_headers = expected_col_headers.difference(current_col_headers)
        error_list.append(
            ValidationError(
                'Erwartete Spaltenköpfe nicht in CSV-Datei gefunden [no subset]! Expected: "{}", got: "{}". Missing headers: "{}"'.format(
                    expected_col_headers,
                    current_col_headers,
                    missing_col_headers,
                )
            )
        )

    for idx, row in enumerate(rows, start=1):
        # Validating items without EDV_ID or SAP_ID
        if (not row["EDV_ID"]) and (not row["SAP_ID"]):
            error_list.append(ValidationError(f"Item in row {idx} without EDV_ID and SAP_ID! Row raw data: {row}"))

        if bulk_mode == "import_devices":
            # Validating clash with already existing Devices
            if row["EDV_ID"].strip() and Device.objects.filter(edv_id=row["EDV_ID"]).exists():
                error_list.append(ValidationError("Device with this EDV_ID already exists: {}".format(row["EDV_ID"])))

            if row["SAP_ID"].strip() and Device.objects.filter(sap_id=row["SAP_ID"]).exists():
                error_list.append(ValidationError("Device with this SAP_ID already exists: {}".format(row["SAP_ID"])))

        if date_fields:
            for key, value in row.items():
                # Validating date format for DateFields
                if key in date_fields:
                    # print(key, value)
                    if value != "":
                        try:
                            datetime.strptime(value, "%Y-%m-%d")
                        except ValueError:
                            error_list.append(
                                ValidationError(
                                    "Incorrect date format, should be YYYY-MM-DD: {}: {}".format(key, value)
                                )
                            )

    if error_list:
        raise ValidationError(error_list)


def set_removed_record(fileobj):
    """
    Mark a device as "removed".
    * Identify device given in CSV, via EDV_ID or SAP_ID or both
    * Search active record for given device
    * Create a new removed-record with attributes given in CSV
    """
    print("[set_removed_record]...")
    now = datetime.now()

    messages = []
    errors_count = 0
    removed_devices_count = 0

    messages.append("[I] Starting set_removed_record...")

    with transaction.atomic():
        csv.register_dialect("custom_dialect", skipinitialspace=True, delimiter=",")
        rows = csv.DictReader(
            codecs.iterdecode(fileobj, "utf-8"),
            dialect="custom_dialect",
        )

        for idx, row in enumerate(rows, start=1):
            # header row is not included in rows (it is in rows.fieldnames),
            # so we do not need to exclude the header row manually

            EDV_ID = row["EDV_ID"].strip()
            SAP_ID = row["SAP_ID"].strip()

            _message = ""
            device = None

            try:
                if SAP_ID and EDV_ID:
                    device = Device.objects.get(edv_id=EDV_ID, sap_id=SAP_ID)
                elif EDV_ID and not SAP_ID:
                    device = Device.objects.get(edv_id=EDV_ID)
                elif SAP_ID and not EDV_ID:
                    device = Device.objects.get(sap_id=SAP_ID)
            except Device.DoesNotExist as does_not_exist_error:
                logger.error(does_not_exist_error)

            if not device:
                messages.append(
                    '[E][Row {}] Device not found: EDV_ID "{}", SAP_ID "{}"! Ignoring this device!'.format(
                        idx, EDV_ID, SAP_ID
                    )
                )
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
                messages.append(
                    '[I][Row {}] Device already "removed": EDV_ID "{}", SAP_ID "{}", Record PK: "{}". Ignoring this device.'.format(
                        idx, EDV_ID, SAP_ID, _already_removed_record.pk
                    )
                )
                continue

            # Create new record for this device
            try:
                record, created = Record.objects.get_or_create(
                    device=device,
                    record_type=Record.REMOVED,
                    note=row["NOTE"],
                    username=row["USERNAME"].strip() if row["USERNAME"] else "",
                    disposition_state=row["DISPOSITION_STATE"],
                    removed_info=row["REMOVED_INFO"],
                    removed_date=row["REMOVED_DATE"] if row["REMOVED_DATE"] else now,
                )
                messages.append("[I][Row {}] Device {} - Record set to removed: {}.".format(idx, device, record.pk))
                removed_devices_count += 1
            except Exception as ex:
                messages.append(
                    '[I][Row {}] "Something bad happend:-(. Please contact your administrator. Exception: "{}"'.format(
                        idx, ex
                    )
                )
                raise

    messages.extend(
        [
            "-------------------------------------------",
            "Errors: {}".format(errors_count),
            "Removed devices: {}".format(removed_devices_count),
            "-------------------------------------------",
        ]
    )
    return "\n".join(messages)


def validate_column_headers(*, current_col_headers, expected_col_headers):
    current_col_headers = set(current_col_headers)
    expected_col_headers = set(expected_col_headers)
    if not expected_col_headers.issubset(current_col_headers):
        missing_col_headers = expected_col_headers.difference(current_col_headers)
        raise ValidationError(
            'Erwartete Spaltenköpfe nicht in CSV-Datei gefunden [no subset]! Expected: "{}", got: "{}". Missing headers: "{}"'.format(
                expected_col_headers,
                current_col_headers,
                missing_col_headers,
            )
        )


def create_record(*, device, record_type, record_note, room, person, username, removed_date):
    from dlcdb.core.models import InRoomRecord, LostRecord, RemovedRecord

    # print(f"Creating record {record_type} for {device}...")
    record_obj = None

    if record_type == Record.INROOM:
        if not room:
            raise ValidationError(f"No room number given for device {device} with record_type {record_type}!")

        # room_obj, created = Room.objects.get_or_create(
        #     number__iexact=room,
        #     defaults={'number': room},
        # )
        room_obj = create_fk_obj(model_class=Room, instance_key="number", instance_value=room)

        record_obj = InRoomRecord(
            device=device,
            room=room_obj,
            note=record_note,
            username=username.strip() if username else "",
        )

    elif record_type == Record.LOST:
        record_obj = LostRecord(
            device=device,
            note=record_note,
            username=username.strip() if username else "",
        )

    elif record_type == Record.REMOVED:
        record_obj = RemovedRecord(
            device=device,
            note=record_note,
            removed_date=removed_date,
            username=username.strip() if username else "",
        )

    return record_obj


def set_datetime_field(value):
    result_value = None

    if value:
        try:
            result_value = datetime.strptime(value, "%Y-%m-%d")
        except ValueError as value_error:
            raise ValueError(f"{value_error}: Incorrect date format, should be YYYY-MM-DD: {value}")

    return result_value


def set_fk_field(row, key):
    obj = None
    value = row[key]

    try:
        model_class_name = string.capwords(key, sep="_").replace("_", "")
        ModelClass = apps.get_model(f"core.{model_class_name}")
        obj = ModelClass.objects.get(name__iexact=value)
    except ModelClass.DoesNotExist as does_not_exist_error:
        raise ObjectDoesNotExist(f"{does_not_exist_error} for {model_class_name} {value}")
    except ModelClass.MultipleObjectsReturned as multiple_objects_returned_error:
        raise IntegrityError(f"{multiple_objects_returned_error} for {model_class_name} {value}")
    except IntegrityError as integrity_error:
        raise IntegrityError(f"{integrity_error} for {model_class_name} {value}")

    return obj.id if obj else None


def create_fk_obj(*, model_class, instance_key, instance_value):
    # instance, created = ModelClass.objects.get_or_create(name=row[fk_field])
    # Get objects with case insensitive lookup or create a new object.
    # Needs to check if dealing with a soft-delete enabled model.
    # print(f"{model_class=}; {instance_key=}: {instance_value=}")

    instance_key_iexact = f"{instance_key}__iexact"
    defaults = {
        instance_key: instance_value,
    }

    if hasattr(model_class, "with_softdeleted_objects"):
        instance, created = model_class.with_softdeleted_objects.get_or_create(
            **{instance_key_iexact: instance_value},
            # name__iexact=instance_value,
            defaults=defaults,
        )

        # Ensure previously soft-deleted objects gets undeleted
        instance.deleted_at = None
        instance.deleted_by = None
        instance.save()
    else:
        instance, created = model_class.objects.get_or_create(
            # name__iexact=instance_value,
            **{instance_key_iexact: instance_value},
            defaults=defaults,
        )

    return instance


def create_fk_objs(fk_field, rows):
    model_class_name = string.capwords(fk_field, sep="_").replace("_", "")
    model_class = apps.get_model(f"core.{model_class_name}")

    for row in rows:
        create_fk_obj(model_class=model_class, instance_key="name", instance_value=row[fk_field])

    return


def create_devices(rows, importer_inst_pk=None, tenant=None, username=None, write=False):
    already_existing_sap_ids = Device.objects.all().values_list("sap_id", flat=True)

    device_objs = []
    record_objs = []
    processed_devices_count = 0
    processed_records_count = 0

    for idx, row in enumerate(rows, start=1):
        # Header row is not included in rows (it is in rows.fieldnames),
        # so we do not need to exclude the header row manually

        # CSV DictReader always returns an empty string. But at
        # database level we need a Null value like None to
        # support our unique constraints for edv_id and sap_id.
        edv_id = row["EDV_ID"] if row["EDV_ID"] else None
        sap_id = row["SAP_ID"] if row["SAP_ID"] else None

        device_repr = f"edv_id: {edv_id or 'n/a'}; sap_id: {sap_id or 'n/a'}"

        # try:
        #     tenant = Tenant.objects.get(name=row['TENANT'])
        # except KeyError as tenant_key_error:
        #     raise ValidationError(
        #         '[Row {}] Device: "{}" NOT imported: TENANT not available in import file! ({})'.format(idx, device_repr, tenant_key_error)
        #     )
        # except ObjectDoesNotExist as tenant_does_not_exists:
        #     raise ValidationError(
        #         '[Row {}] Device: "{}" NOT imported: TENANT "{}" does not exist! ({})'.format(idx, device_repr, row['TENANT'], tenant_does_not_exists)
        #     )

        # Booleans
        is_lentable = True if row["IS_LENTABLE"].lower() in TRUE_VALUES else False
        is_licence = True if row["IS_LICENCE"].lower() in TRUE_VALUES else False

        device_obj = Device(
            is_imported=True,
            imported_by_id=importer_inst_pk,
            # these fields should be mappable without further processing:
            username=username if username else "",
            book_value=row["BOOK_VALUE"],
            serial_number=row["SERIAL_NUMBER"],
            series=row["SERIES"],
            cost_centre=row["COST_CENTRE"],
            note=row["NOTE"],
            mac_address=row["MAC_ADDRESS"],
            extra_mac_addresses=row["EXTRA_MAC_ADDRESSES"],
            nick_name=row["NICK_NAME"],
            order_number=row["ORDER_NUMBER"],
            # These fields need some pre-processing
            edv_id=edv_id,
            sap_id=sap_id,
            tenant=tenant,
            # FK fields
            manufacturer_id=set_fk_field(row, "MANUFACTURER"),
            device_type_id=set_fk_field(row, "DEVICE_TYPE"),
            supplier_id=set_fk_field(row, "SUPPLIER"),
            # Boolean fields
            is_lentable=is_lentable,
            is_licence=is_licence,
            # Date fields
            purchase_date=set_datetime_field(row["PURCHASE_DATE"]),
            warranty_expiration_date=set_datetime_field(row["WARRANTY_EXPIRATION_DATE"]),
            maintenance_contract_expiration_date=set_datetime_field(row["MAINTENANCE_CONTRACT_EXPIRATION_DATE"]),
        )

        # If the sap_id already exists in our DLCDB, we skip and do not import
        # this asset!
        if sap_id not in already_existing_sap_ids:
            device_objs.append(device_obj)
            record_objs.append(
                create_record(
                    device=device_obj,
                    record_type=row["RECORD_TYPE"],
                    record_note=row["RECORD_NOTE"],
                    room=row["ROOM"],
                    person=row["PERSON"],
                    username=username,
                    removed_date=row["REMOVED_DATE"],
                )
            )
    try:
        if write:
            # As bulk_create() does not call model.save() method, we can not use it for now
            # _bulk_create_supported = True
            # # Use bulk_create for newer versions of sqlite to avoid
            # # Exception Value: bulk_create() prohibited to prevent data loss due to unsaved related object 'device'.
            # # See: https://docs.djangoproject.com/en/4.1/ref/models/querysets/#bulk-create
            # # Changed in Django 4.0: Support for the fetching primary key attributes on SQLite 3.35+ was added.
            # if connection.vendor == 'sqlite':
            #     import sqlite3
            #     from packaging import version

            #     installed_sqlite_version = version.parse(sqlite3.sqlite_version)
            #     requested_sqlite_version = version.parse("3.35")

            #     if installed_sqlite_version < requested_sqlite_version:
            #         _bulk_create_supported = False

            # if _bulk_create_supported:
            #     Device.objects.bulk_create(device_objs)
            #     Record.objects.bulk_create([record for record in record_objs if record is not None])
            # else:

            for device in device_objs:
                device.save()

            for record in record_objs:
                if record:
                    record.save()

        else:
            # In dryrun mode
            for device_obj in device_objs:
                device_obj.save()
                processed_devices_count += 1

            for record_obj in record_objs:
                if record_obj:
                    record_obj.save()
                    processed_records_count += 1

        # print(f"Created {processed_devices_count} devices.")
        # print(f"Created {processed_records_count} records.")
    except IntegrityError as integrity_error:
        raise IntegrityError(f"IntegrityError {integrity_error} for {device_repr}")
    except ValueError as value_error:
        raise ValueError(f"ValueError {value_error} for {device_repr}")
    except Exception as base_exception:
        raise IntegrityError(f"Exception {base_exception} for {device_repr}")

    return device_objs


def import_data(
    csvfile, tenant, username=None, importer_inst_pk=None, import_format=None, valid_col_headers=None, write=False
):
    from ..models import ImporterList

    if import_format == ImporterList.ImportFormatChoices.INTERNALCSV:
        csvfile.seek(0)
        csvfile = StringIO(csvfile.read().decode("utf-8"))
    elif import_format == ImporterList.ImportFormatChoices.SAPCSV:
        csvfile = convert_raw_sap_export(csvfile, tenant, valid_col_headers)
    else:
        raise ValidationError("Import format not specified.")

    ImporterMessages = namedtuple(
        "ImporterMessages",
        [
            "success_messages",
            "imported_devices_count",
            "error",
        ],
    )
    success_messages = []

    if write:
        atomic_context = atomic()
    else:
        atomic_context = rollback_atomic()

    with atomic_context:
        csv.register_dialect("custom_dialect", skipinitialspace=True, delimiter=",")
        rows = csv.DictReader(
            # codecs.iterdecode(csvfile, 'utf-8'),
            csvfile,
            dialect="custom_dialect",
        )

        validate_column_headers(current_col_headers=rows.fieldnames, expected_col_headers=valid_col_headers)

        # https://cs205uiuc.github.io/guidebook/python/csv.html
        rows = [row for row in rows]

        # First loop over rows: Creating foreign key instances
        fk_fields = ["SUPPLIER", "MANUFACTURER", "DEVICE_TYPE"]
        for fk_field in fk_fields:
            create_fk_objs(fk_field, rows)

        # Second loop over rows: Creating devices
        try:
            device_objs = create_devices(
                rows, importer_inst_pk=importer_inst_pk, tenant=tenant, username=username, write=write
            )
        except ValueError as value_error:
            raise ValueError(value_error)
        else:
            result = ImporterMessages(
                success_messages,
                f"Imported devices: {len(device_objs)}",
                error=False,
            )
    return result
