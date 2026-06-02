# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Importer für Device-Listen im CSV-Format
"""

import csv
import logging
import secrets
from dataclasses import dataclass
from io import StringIO

from django.db.transaction import atomic
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from dlcdb.core.models import Device, Record
from dlcdb.core.utils.helpers import rollback_atomic

from .models import ImporterList
from .reporting import OperationReport, Outcome
from .sap_converter import convert_raw_sap_export
from .validators import validate_column_headers
from .fields import set_fk_field, set_datetime_field, set_date_field, create_fk_objs
from .records import create_record


logger = logging.getLogger(__name__)


TRUE_VALUES = ("yes", "ja", "true", "1")


def _import_transaction(*, import_objs, import_format, report, device_objs, tenant=None):
    if import_format == "SAPCSV":
        for import_obj in import_objs:
            device_obj = import_obj.device
            # SAP imports never produce LENT rows, so records holds 0 or 1 record.
            records = import_obj.records

            # Cases for SAP import:
            # - sap_id already exists in other tenant -> do nothing, DLCDB data is the leading system
            # - sap_id does not exist -> create new device for tenant "Foo" and set new record
            # - sap_id already exists in tenant "Foo" -> update room only (if not already set)
            # - sap_id exists but deactivated -> set new RemovedRecord (if not already set)

            already_existing_device = Device.objects.filter(sap_id=device_obj.sap_id).first()

            if already_existing_device and all([already_existing_device.tenant.name == tenant.name, records]):
                logger.debug("Device %s already exists in tenant %s. Updating record only.", device_obj, tenant)
                for record_obj in records:
                    record_obj.device = already_existing_device
                    record_obj.save()
                report.add(
                    row=import_obj.row,
                    identifier=import_obj.identifier,
                    outcome=Outcome.UPDATED,
                    detail=f"record only; device exists in tenant '{tenant}'",
                )

            elif not already_existing_device:
                logger.debug("Device %s does not exist. Creating new device.", device_obj)
                detail = ""

                if Device.objects.filter(edv_id=device_obj.edv_id).exists():
                    new_edv_id = f"{device_obj.edv_id}-UNIQ{secrets.token_hex(4)}"
                    logger.debug("edv_id %s already exists. Renaming to %s.", device_obj.edv_id, new_edv_id)
                    detail = f"edv_id collision -> {new_edv_id}"
                    device_obj.edv_id = new_edv_id

                device_obj.save()
                device_objs.append(device_obj)
                for record_obj in records:
                    record_obj.save()
                report.add(
                    row=import_obj.row,
                    identifier=import_obj.identifier,
                    outcome=Outcome.CREATED,
                    detail=detail,
                )

            else:
                other_tenant = already_existing_device.tenant
                if other_tenant and other_tenant.name != tenant.name:
                    detail = f"exists in other tenant '{other_tenant}'"
                else:
                    detail = "already exists; no record to update"
                logger.debug("Skipping device %s: %s", device_obj, detail)
                report.add(
                    row=import_obj.row,
                    identifier=import_obj.identifier,
                    outcome=Outcome.SKIPPED,
                    detail=detail,
                )

    else:
        for import_obj in import_objs:
            import_obj.device.save()
            device_objs.append(import_obj.device)
            # Save records in order; the last one saved becomes the active record
            # (e.g. for a completed loan: LENT first, then the active INROOM).
            for record_obj in import_obj.records:
                record_obj.save()
            report.add(row=import_obj.row, identifier=import_obj.identifier, outcome=Outcome.CREATED)

    return device_objs


@dataclass
class ImportObject:
    """
    An ImportObject is defined by a device and its related records (if any),
    plus its originating CSV row number and a human-readable identifier.

    A single CSV row usually maps to one record, but a completed loan (a LENT
    row with a lent_end_date) maps to two ordered records: the LENT record
    followed by an INROOM record. Records are saved in list order; the last
    one saved becomes the device's active record.
    """

    device: Device
    records: list[Record]
    row: int
    identifier: str


def create_devices(*, rows, report, importer_inst_pk=None, import_format=None, tenant=None, username=None, write=False):
    import_objs = []
    device_objs = []

    for idx, row in enumerate(rows, start=1):
        # Header row is not included in rows (it is in rows.fieldnames),
        # so we do not need to exclude the header row manually

        # CSV DictReader always returns an empty string. But at
        # database level we need a Null value like None to
        # support our unique constraints for edv_id and sap_id.
        edv_id = row["EDV_ID"] if row["EDV_ID"] else None
        sap_id = row["SAP_ID"] if row["SAP_ID"] else None

        identifier = f"EDV_ID={edv_id or '—'} SAP_ID={sap_id or '—'}"
        logger.debug("Processing device %s ...", identifier)

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

        record_objs = create_record(
            device=device_obj,
            record_type=row["RECORD_TYPE"],
            record_note=row["RECORD_NOTE"],
            room=row["ROOM"],
            username=username,
            removed_date=set_datetime_field(row["REMOVED_DATE"]),
            lender_first_name=row["LENDER_FIRST_NAME"],
            lender_last_name=row["LENDER_LAST_NAME"],
            lender_email=row["LENDER_EMAIL"],
            lender_ou=row["LENDER_OU"],
            lent_start_date=set_date_field(row["LENT_START_DATE"]),
            lent_desired_end_date=set_date_field(row["LENT_DESIRED_END_DATE"]),
            lent_end_date=set_date_field(row["LENT_END_DATE"]),
            lent_note=row["LENT_NOTE"],
            lent_reason=row["LENT_REASON"],
            lent_accessories=row["LENT_ACCESSORIES"],
        )

        import_objs.append(ImportObject(device=device_obj, records=record_objs, row=idx, identifier=identifier))

    try:
        # As bulk_create() does not call model.save() method, we do not use it for now
        logger.debug("%s transaction...", "Write" if write else "Simulate")
        device_objs = _import_transaction(
            import_objs=import_objs,
            import_format=import_format,
            report=report,
            device_objs=device_objs,
            tenant=tenant,
        )
    except IntegrityError as integrity_error:
        raise IntegrityError(f"IntegrityError {integrity_error}")
    except ValueError as value_error:
        raise ValueError(f"ValueError {value_error}")
    except Exception as base_exception:
        raise Exception(f"Exception {base_exception}") from base_exception

    return device_objs


def import_data(
    csvfile, *, tenant, username=None, importer_inst_pk=None, import_format=None, valid_col_headers=None, write=False
):
    if import_format == ImporterList.ImportFormatChoices.INTERNALCSV:
        csvfile.seek(0)
        csvfile = StringIO(csvfile.read().decode("utf-8"))
    elif import_format == ImporterList.ImportFormatChoices.SAPCSV:
        csvfile = convert_raw_sap_export(csvfile, tenant, valid_col_headers)
    else:
        raise ValidationError("Import format not specified.")

    report = OperationReport(operation="Import", context=f"{import_format}, tenant: {tenant}", dry_run=not write)

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
        create_devices(
            rows=rows,
            report=report,
            importer_inst_pk=importer_inst_pk,
            import_format=import_format,
            tenant=tenant,
            username=username,
            write=write,
        )

    return report
