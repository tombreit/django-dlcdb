# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Bulk decommissioning: mark devices as "removed" from a CSV list.
"""

import csv
import logging
from io import StringIO
from datetime import datetime

from django.db.transaction import atomic
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from dlcdb.core.models import Device, Record
from dlcdb.core.utils.helpers import rollback_atomic

from .models import RemoverList
from .reporting import OperationReport, Outcome
from .validators import validate_column_headers


logger = logging.getLogger(__name__)


def set_removed_record(csvfile, *, username=None, write=False):
    """
    Mark a device as "removed".
    * Identify device given in CSV, via EDV_ID or SAP_ID or both
    * Search active record for given device
    * Create a new removed-record with attributes given in CSV

    Fails loudly: a missing/ambiguous device or an already-removed device aborts
    the whole batch (the surrounding transaction is rolled back).
    """

    report = OperationReport(operation="Decommission", dry_run=not write)

    csv.register_dialect("custom_dialect", skipinitialspace=True, delimiter=",")

    # Read and decode the file content
    try:
        csvfile.seek(0)  # Reset file pointer to the beginning
        decoded_content = csvfile.read().decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValidationError(f"Error decoding CSV file: {e}")

    # Use StringIO to create a text-based file-like object
    csvfile_text = StringIO(decoded_content)

    rows = csv.DictReader(
        csvfile_text,  # Pass the text-based file-like object
        dialect="custom_dialect",
    )

    validate_column_headers(current_col_headers=rows.fieldnames, expected_col_headers=RemoverList.VALID_COL_HEADERS)

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
            identifier = f"EDV_ID={EDV_ID or '—'} SAP_ID={SAP_ID or '—'}"

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
                report.add(
                    row=idx,
                    identifier=identifier,
                    outcome=Outcome.REMOVED,
                    detail=f"new REMOVED record: {record.pk}",
                )

    return report
