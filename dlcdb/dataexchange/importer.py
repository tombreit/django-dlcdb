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

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from dlcdb.core.models import Device, Record
from dlcdb.core.utils.helpers import rollback_atomic

from .fields import create_fk_objs, set_date_field, set_datetime_field, set_fk_field
from .models import ImporterList
from .records import create_record
from .reporting import OperationReport, Outcome
from .sap_converter import convert_raw_sap_export
from .validators import validate_column_headers

logger = logging.getLogger(__name__)


TRUE_VALUES = ("yes", "ja", "true", "1")

# The error types an import can legitimately fail with. Shared by every caller
# (frontend views, admin form, admin save_model) so the two importers surface the
# same failures the same way instead of one of them raising a 500.
IMPORT_ERRORS = (ValidationError, ValueError, IntegrityError, ObjectDoesNotExist)


def import_error_message(error):
    """The human-readable text of an import error.

    A ValidationError keeps its messages in a list; everything else stringifies.
    """
    if isinstance(error, ValidationError):
        return "; ".join(error.messages)
    return str(error)


def _row_error_detail(error):
    """The per-row ``detail`` text for a failed CSV row.

    The row number and the device identifier are carried by the report row
    itself, so this only has to explain *what* went wrong. Raw unique-constraint
    text ("UNIQUE constraint failed: core_device.edv_id") is prefixed with a
    plain-language reading -- that bare string was the whole of the error message
    users used to get.
    """
    message = import_error_message(error)

    if isinstance(error, IntegrityError) and "unique" in message.lower():
        return _("a device with this EDV_ID or SAP_ID already exists. Original error: %(error)s") % {"error": message}

    return message


def _describe_records(records):
    """One short, translated line saying what a CSV row writes.

    Deliberately terse: the import preview should say what kind of record a row
    produces plus the one or two facts that identify it, not repeat the row.

    Call this only after the records have been saved -- the record proxies stamp
    ``record_type`` in their ``save()``, so before that the type is still empty.
    """
    if not records:
        return _("new device, no record")

    record = records[0]

    if record.record_type == Record.INROOM:
        return _("new device, in room %(room)s") % {"room": record.room.number}

    if record.record_type == Record.LENT:
        # A returned loan is a LENT record followed by the INROOM record that
        # brings the device back (see create_record).
        template = (
            _("new device, lent to %(lender)s (room %(room)s), returned")
            if len(records) > 1
            else _("new device, lent to %(lender)s (room %(room)s)")
        )
        return template % {"lender": record.person.email, "room": record.room.number}

    if record.record_type == Record.LOST:
        return _("new device, not locatable")

    # RemovedRecord.save() always stamps a removed_date, so a saved removal has one.
    if record.record_type == Record.REMOVED and record.removed_date:
        removed_date = date_format(timezone.localtime(record.removed_date), format="DATE_FORMAT")
        return _("new device, removed on %(date)s") % {"date": removed_date}

    return _("new device, record %(record_type)s") % {"record_type": record.get_record_type_display()}


def _import_transaction(*, import_objs, import_format, report, device_objs, tenant=None):
    if import_format == "SAPCSV":
        for import_obj in import_objs:
            try:
                # Same savepoint-per-row treatment as the internal-CSV branch below,
                # so both formats report a bad row the same way instead of one of
                # them aborting the whole file.
                with transaction.atomic():
                    device_obj = import_obj.device
                    # SAP imports never produce LENT rows, so records holds 0 or 1 record.
                    records = import_obj.records

                    # Cases for SAP import:
                    # - sap_id already exists in other tenant -> do nothing, DLCDB data is the leading system
                    # - sap_id does not exist -> create new device for tenant "Foo" and set new record
                    # - sap_id already exists in tenant "Foo" -> update room only (if not already set)
                    # - sap_id exists but deactivated -> set new RemovedRecord (if not already set)

                    already_existing_device = Device.objects.filter(sap_id=device_obj.sap_id).first()

                    # Compare ids: an already existing device may have no tenant at all.
                    if already_existing_device and all([already_existing_device.tenant_id == tenant.pk, records]):
                        logger.debug("Device %s already exists in tenant %s. Updating record only.", device_obj, tenant)
                        for record_obj in records:
                            record_obj.device = already_existing_device
                            record_obj.save(check_transition=False)
                        report.add(
                            row=import_obj.row,
                            identifier=import_obj.identifier,
                            outcome=Outcome.UPDATED,
                            detail=_("record only; device exists in tenant '%(tenant)s'") % {"tenant": tenant},
                        )

                    elif not already_existing_device:
                        logger.debug("Device %s does not exist. Creating new device.", device_obj)
                        detail = ""

                        if Device.objects.filter(edv_id=device_obj.edv_id).exists():
                            new_edv_id = f"{device_obj.edv_id}-UNIQ{secrets.token_hex(4)}"
                            logger.debug("edv_id %s already exists. Renaming to %s.", device_obj.edv_id, new_edv_id)
                            detail = _("edv_id collision -> %(new_edv_id)s") % {"new_edv_id": new_edv_id}
                            device_obj.edv_id = new_edv_id

                        device_obj.save()
                        device_objs.append(device_obj)
                        for record_obj in records:
                            record_obj.save(check_transition=False)
                        report.add(
                            row=import_obj.row,
                            identifier=import_obj.identifier,
                            outcome=Outcome.CREATED,
                            detail=detail,
                        )

                    else:
                        other_tenant = already_existing_device.tenant
                        if other_tenant and other_tenant.name != tenant.name:
                            detail = _("exists in other tenant '%(tenant)s'") % {"tenant": other_tenant}
                        else:
                            detail = _("already exists; no record to update")
                        logger.debug("Skipping device %s: %s", device_obj, detail)
                        report.add(
                            row=import_obj.row,
                            identifier=import_obj.identifier,
                            outcome=Outcome.SKIPPED,
                            detail=detail,
                        )
            except Exception as error:
                detail = _row_error_detail(error)
                # Not journaled: the import's own journal entry lists the row.
                logger.warning(
                    "Row %s (%s) failed: %s", import_obj.row, import_obj.identifier, detail, extra={"journal": False}
                )
                report.add(
                    row=import_obj.row,
                    identifier=import_obj.identifier,
                    outcome=Outcome.ERROR,
                    detail=detail,
                )

    else:
        for import_obj in import_objs:
            try:
                # Each row writes inside its own savepoint: a failed write (a
                # duplicate edv_id/sap_id, say) rolls back in isolation, so it
                # neither aborts the run nor poisons the surrounding transaction
                # for the rows that follow.
                with transaction.atomic():
                    import_obj.device.save()
                    # Save records in order; the last one saved becomes the active record
                    # (e.g. for a completed loan: LENT first, then the active INROOM).
                    # check_transition=False: the import replays arbitrary historical
                    # chains (a device may be imported straight into any state), which the
                    # live lifecycle would reject.
                    for record_obj in import_obj.records:
                        record_obj.save(check_transition=False)
            except Exception as error:
                detail = _row_error_detail(error)
                # Not journaled: the import's own journal entry lists the row.
                logger.warning(
                    "Row %s (%s) failed: %s", import_obj.row, import_obj.identifier, detail, extra={"journal": False}
                )
                report.add(
                    row=import_obj.row,
                    identifier=import_obj.identifier,
                    outcome=Outcome.ERROR,
                    detail=detail,
                )
                continue

            device_objs.append(import_obj.device)
            report.add(
                row=import_obj.row,
                identifier=import_obj.identifier,
                outcome=Outcome.CREATED,
                detail=_describe_records(import_obj.records),
            )

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

    # Resolve the importing user once for the audit `user` FK (the denormalized
    # `username` string is set separately). Hard lookup like remover.py: an
    # import must be attributable to a real user.
    user_obj = None
    if username:
        user_model = get_user_model()
        try:
            user_obj = user_model.objects.get(username=username)
        except user_model.DoesNotExist as user_does_not_exist_error:
            raise user_model.DoesNotExist(f'User "{username}" not found! ({user_does_not_exist_error})')

    # start=2 so the reported number is the line the user sees in their
    # spreadsheet: the header is line 1 and is not part of `rows`.
    for idx, row in enumerate(rows, start=2):
        # CSV DictReader always returns an empty string. But at
        # database level we need a Null value like None to
        # support our unique constraints for edv_id and sap_id.
        edv_id = row["EDV_ID"] if row["EDV_ID"] else None
        sap_id = row["SAP_ID"] if row["SAP_ID"] else None

        identifier = f"EDV_ID={edv_id or '—'} SAP_ID={sap_id or '—'}"
        logger.debug("Processing device %s ...", identifier)

        try:
            # One savepoint per row. Catching an IntegrityError inside the
            # surrounding atomic() without one would leave the transaction
            # unusable on PostgreSQL, so the savepoint is required, not tidiness.
            with transaction.atomic():
                # Booleans
                is_lentable = row["IS_LENTABLE"].lower() in TRUE_VALUES
                is_licence = row["IS_LICENCE"].lower() in TRUE_VALUES

                device_obj = Device(
                    is_imported=True,
                    imported_by_id=importer_inst_pk,
                    # These fields should be mappable without further processing:
                    user=user_obj,
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
                    purchase_date=set_datetime_field(row["PURCHASE_DATE"], column="PURCHASE_DATE"),
                    warranty_expiration_date=set_datetime_field(
                        row["WARRANTY_EXPIRATION_DATE"], column="WARRANTY_EXPIRATION_DATE"
                    ),
                    contract_expiration_date=set_datetime_field(
                        row["CONTRACT_EXPIRATION_DATE"], column="CONTRACT_EXPIRATION_DATE"
                    ),
                )

                record_objs = create_record(
                    device=device_obj,
                    record_type=row["RECORD_TYPE"],
                    record_note=row["RECORD_NOTE"],
                    room=row["ROOM"],
                    username=username,
                    user=user_obj,
                    removed_date=set_datetime_field(row["REMOVED_DATE"], column="REMOVED_DATE"),
                    lender_first_name=row["LENDER_FIRST_NAME"],
                    lender_last_name=row["LENDER_LAST_NAME"],
                    lender_email=row["LENDER_EMAIL"],
                    lender_ou=row["LENDER_OU"],
                    lent_start_date=set_date_field(row["LENT_START_DATE"], column="LENT_START_DATE"),
                    lent_desired_end_date=set_date_field(row["LENT_DESIRED_END_DATE"], column="LENT_DESIRED_END_DATE"),
                    lent_end_date=set_date_field(row["LENT_END_DATE"], column="LENT_END_DATE"),
                    lent_note=row["LENT_NOTE"],
                    lent_reason=row["LENT_REASON"],
                    lent_accessories=row["LENT_ACCESSORIES"],
                )

                import_objs.append(ImportObject(device=device_obj, records=record_objs, row=idx, identifier=identifier))
        except Exception as error:
            # One bad row must not abort the file: record it with its line
            # number and identifier and carry on, so the dry run surfaces every
            # problem at once instead of one per re-upload.
            detail = _row_error_detail(error)
            # Not journaled: the import's own journal entry lists the row.
            logger.warning("Row %s (%s) failed: %s", idx, identifier, detail, extra={"journal": False})
            report.add(row=idx, identifier=identifier, outcome=Outcome.ERROR, detail=detail)
            continue

    # As bulk_create() does not call model.save() method, we do not use it for now.
    # Errors propagate with their original type: the wrapper that used to sit here
    # only prefixed the class name, and its `raise Exception(...)` branch erased the
    # very types the callers catch, turning a form error into a 500.
    logger.debug("%s transaction...", "Write" if write else "Simulate")
    device_objs = _import_transaction(
        import_objs=import_objs,
        import_format=import_format,
        report=report,
        device_objs=device_objs,
        tenant=tenant,
    )

    return device_objs


def run_device_import(*, file, tenant, import_format, user, importer_list=None, write=False):
    """
    Single entry point for device imports, shared by the admin and the frontend.

    Runs import_data() against ImporterList.VALID_COL_HEADERS. When write=True
    and an ImporterList instance is given, created devices are linked to it and
    the report is persisted on it. A failed attempt is part of the import
    history too: it is recorded on the given ImporterList row (status "error"
    plus the error text in the log) before the exception is re-raised.

    Every outcome stored on the row also becomes a journal entry naming
    ``user``, whoever runs this import.
    """
    try:
        report = import_data(
            file,
            importer_inst_pk=importer_list.pk if importer_list else None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=import_format,
            tenant=tenant,
            username=user.username,
            write=write,
        )
    except Exception as error:
        if importer_list is not None and importer_list.pk:
            # Written after the import's transaction has rolled back, so the
            # row and its journal entry survive the failure.
            error_text = import_error_message(error)
            importer_list.status = ImporterList.Status.ERROR
            importer_list.summary = error_text[:255]
            importer_list.messages = f"{'Import' if write else 'Import check (dry run)'} failed: {error_text}"
            importer_list.save()
            importer_list.write_journal(event="failed" if write else "dry_run_failed", user=user)
        raise

    if importer_list is not None and (write or report.counts[Outcome.ERROR]):
        # A dry run that found bad rows is a failed attempt too, and belongs in the
        # import history with its per-row reasons -- otherwise the audit row keeps
        # an empty status and the user loses the detail on the next upload.
        report.persist(importer_list)
        importer_list.write_journal(event="imported" if write else "dry_run_failed", user=user)
    return report


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
        atomic_context = transaction.atomic()
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

        # Belt and braces: the preview blocks the confirm button while any row is
        # in error, but a write must never half-apply a file the user was shown
        # errors for. Raising inside the atomic block rolls the whole thing back.
        error_count = report.counts[Outcome.ERROR]
        if write and error_count:
            raise ValidationError(
                _("Import aborted: %(count)s row(s) could not be imported. Nothing was written.")
                % {"count": error_count}
            )

    return report
