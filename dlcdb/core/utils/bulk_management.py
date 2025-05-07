# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Importer für Device-Listen im CSV-Format
"""

import csv
import string
import logging
import secrets
from dataclasses import dataclass
from io import StringIO
from collections import namedtuple

from datetime import datetime

from django.db.transaction import atomic
from django.db import IntegrityError
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware

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


def set_removed_record(csvfile, username=None, write=False):
    """
    Mark a device as "removed".
    * Identify device given in CSV, via EDV_ID or SAP_ID or both
    * Search active record for given device
    * Create a new removed-record with attributes given in CSV
    """

    RemovedMessages = namedtuple(
        "RemovedMessages",
        [
            "success_messages",
            "removed_devices_count",
            "error",
        ],
    )
    success_messages = []
    removed_devices_count = 0

    csv.register_dialect("custom_dialect", skipinitialspace=True, delimiter=",")

    # Read and decode the file content
    try:
        csvfile.seek(0)  # Reset file pointer to the beginning
        decoded_content = csvfile.read().decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValidationError(f"Error decoding CSV file: {e}")

    # Use StringIO to create a text-based file-like object
    csvfile_text = StringIO(decoded_content)

    print(f"{csvfile_text=}")

    rows = csv.DictReader(
        csvfile_text,  # Pass the text-based file-like object
        dialect="custom_dialect",
    )

    if write:
        atomic_context = atomic()
    else:
        atomic_context = rollback_atomic()

    with atomic_context:
        for idx, row in enumerate(rows, start=1):
            try:
                user_model = get_user_model()
                user = user_model.objects.get(username=username)
            except user_model.DoesNotExist as user_does_not_exist_error:
                raise user_model.DoesNotExist(
                    f'[E][Row {idx}] User "{username}" not found! ({user_does_not_exist_error})'
                )

            EDV_ID = row.get("EDV_ID", "").strip()
            SAP_ID = row.get("SAP_ID", "").strip()

            if not (SAP_ID or EDV_ID):
                raise Device.DoesNotExist(f"No device identifiers provided: empty SAP_ID and EDV_ID (row {idx})")

            try:
                if SAP_ID and EDV_ID:
                    device = Device.objects.get(edv_id=EDV_ID, sap_id=SAP_ID)
                elif EDV_ID:
                    device = Device.objects.get(edv_id=EDV_ID)
                elif SAP_ID:
                    device = Device.objects.get(sap_id=SAP_ID)
            except Device.DoesNotExist as does_not_exist_error:
                raise Device.DoesNotExist(f"Device {SAP_ID=} or {EDV_ID=} does not exist. {does_not_exist_error}")

            print(f"{device=}")

            # Check if the current record for this device is already a 'removed' record
            _already_removed_record = Record.objects.filter(
                Q(is_active=True),
                Q(device=device),
                Q(record_type=Record.REMOVED),
            ).first()

            if _already_removed_record:
                raise ValidationError(
                    f'[Row {idx}] Device already "removed": {EDV_ID=}, {SAP_ID=}, Record PK: "{_already_removed_record.pk}".'
                )

            # Create new record for this device
            try:
                record, created = Record.objects.get_or_create(
                    device=device,
                    record_type=Record.REMOVED,
                    note=row["NOTE"],
                    username=username,
                    user=user,
                    disposition_state=row["DISPOSITION_STATE"],
                    removed_info=row["REMOVED_INFO"],
                    removed_date=row["REMOVED_DATE"] if row["REMOVED_DATE"] else datetime.now(),
                )
            except KeyError as key_error:
                raise KeyError(f"KeyError {key_error} for {device}")
            except Exception as ex:
                raise Exception(f"Error creating record for {device}: {ex}")
            else:
                removed_devices_count += 1
                success_messages.append(f"Device {device} removed. New REMOVED record: {record.pk}.")

            result = RemovedMessages(
                success_messages,
                f"Removed devices: {removed_devices_count}",
                error=False,
            )

    return result


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
            result_value = make_aware(result_value)
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


def _import_transaction(import_objs, import_format, device_objs, tenant=None):
    processed_devices_count = 0
    processed_records_count = 0
    import_msg = ""

    if import_format == "SAPCSV":
        for import_obj in import_objs:
            print(80 * "=")
            device_obj = import_obj.device
            record_obj = import_obj.record

            # Cases for SAP import:
            # - sap_id already exists in other tenant -> do nothing, DLCDB data is the leading system
            # - sap_id does not exist -> create new device for tenant "Foo" and set new record
            # - sap_id already exists in tenant "Foo" -> update room only (if not already set)
            # - sap_id exists but deactivated -> set new RemovedRecord (if not already set)

            already_existing_device = Device.objects.filter(sap_id=device_obj.sap_id).first()

            if already_existing_device and all(
                [
                    already_existing_device.tenant.name == tenant.name,
                    record_obj,
                ]
            ):
                print(f"Device {device_obj} already exists in tenant {tenant}. Updating record only.")
                record_obj.device = already_existing_device
                record_obj.save()
                processed_records_count += 1

            elif not already_existing_device:
                print(f"Device {device_obj} does not exist. Creating new device.")

                if Device.objects.filter(edv_id=device_obj.edv_id).exists():
                    print(f"Device with edv_id {device_obj.edv_id} already exists. Adding random suffix.")
                    device_obj.edv_id = f"{device_obj.edv_id}-UNIQ{secrets.token_hex(4)}"

                device_obj.save()
                processed_devices_count += 1
                device_objs.append(device_obj)

                if record_obj:
                    record_obj.save()
                    processed_records_count += 1

    else:
        for import_obj in import_objs:
            import_obj.device.save()
            device_objs.append(import_obj.device)
            processed_devices_count += 1

            if import_obj.record:
                import_obj.record.save()
                processed_records_count += 1

    import_msg = f"Processed devices: {processed_devices_count}, processed records: {processed_records_count}"

    return device_objs, import_msg


@dataclass
class ImportObject:
    """
    An ImportObject is defined by a device and a related record (if available).
    """

    device: Device
    record: Record | None


def create_devices(rows, importer_inst_pk=None, import_format=None, tenant=None, username=None, write=False):
    import_objs = []
    device_objs = []

    for idx, row in enumerate(rows, start=1):
        # print(f"{row=}")
        # Header row is not included in rows (it is in rows.fieldnames),
        # so we do not need to exclude the header row manually

        # CSV DictReader always returns an empty string. But at
        # database level we need a Null value like None to
        # support our unique constraints for edv_id and sap_id.
        edv_id = row["EDV_ID"] if row["EDV_ID"] else None
        sap_id = row["SAP_ID"] if row["SAP_ID"] else None

        device_repr = f"edv_id: {edv_id or 'n/a'}; sap_id: {sap_id or 'n/a'}"
        print(f"Processing device {device_repr} ...")

        # Booleans
        is_lentable = True if row["IS_LENTABLE"].lower() in TRUE_VALUES else False
        is_licence = True if row["IS_LICENCE"].lower() in TRUE_VALUES else False

        device_obj = Device(
            is_imported=True,
            imported_by_id=importer_inst_pk,
            # These fields should be mappable without further processing:
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
            contract_expiration_date=set_datetime_field(row["CONTRACT_EXPIRATION_DATE"]),
        )

        record_obj = create_record(
            device=device_obj,
            record_type=row["RECORD_TYPE"],
            record_note=row["RECORD_NOTE"],
            room=row["ROOM"],
            person=row["PERSON"],
            username=username,
            removed_date=set_datetime_field(row["REMOVED_DATE"]),
        )

        import_objs.append(ImportObject(device=device_obj, record=record_obj))

    try:
        if write:
            # As bulk_create() does not call model.save() method, we do not use it for now
            print("Write transaction...")

            device_objs = _import_transaction(
                import_objs=import_objs,
                import_format=import_format,
                device_objs=device_objs,
                tenant=tenant,
            )

        else:
            print("Simulate transaction...")

            device_objs = _import_transaction(
                import_objs=import_objs,
                import_format=import_format,
                device_objs=device_objs,
                tenant=tenant,
            )

    except IntegrityError as integrity_error:
        raise IntegrityError(f"IntegrityError {integrity_error} for {device_repr}")
    except ValueError as value_error:
        raise ValueError(f"ValueError {value_error} for {device_repr}")
    except Exception as base_exception:
        raise Exception(f"Exception {base_exception}") from base_exception

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

        # Read and decode the file content
        try:
            csvfile.seek(0)  # Reset file pointer to the beginning
            content = csvfile.read()
            if isinstance(content, bytes):
                decoded_content = content.decode("utf-8")
            else:
                # Assume it's already a string (decoded)
                decoded_content = content
        except UnicodeDecodeError as e:
            raise ValidationError(f"Error decoding CSV file: {e}")
        except AttributeError as e:
            raise AttributeError(f"Error reading or processing CSV file: {e}")

        # Use StringIO to create a text-based file-like object
        csvfile_text = StringIO(decoded_content)

        rows = csv.DictReader(
            csvfile_text,  # Pass the text-based file-like object
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
            device_objs, import_msg = create_devices(
                rows,
                importer_inst_pk=importer_inst_pk,
                import_format=import_format,
                tenant=tenant,
                username=username,
                write=write,
            )
        except ValueError as value_error:
            raise ValueError(value_error)
        else:
            result = ImporterMessages(
                success_messages,
                f"Imported devices: {len(device_objs)}. {import_msg}",
                error=False,
            )
    return result
