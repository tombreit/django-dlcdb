# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Bulk decommissioning: mark devices as "removed" from a CSV list.
"""

import csv
import logging
from io import StringIO
from django.utils import timezone
from django.db.transaction import atomic
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from dlcdb.core import lifecycle
from dlcdb.core.models import Device
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

            # Append a REMOVED record via the lifecycle. transition_remove routes
            # through the RemovedRecord proxy (which nulls the room and defaults
            # removed_date -- the old get_or_create on a plain Record did neither),
            # and its source-state check rejects removing an already-removed device.
            try:
                record = lifecycle.transition_remove(
                    device,
                    disposition_state=row["DISPOSITION_STATE"],
                    removed_info=row["REMOVED_INFO"],
                    note=row["NOTE"],
                    removed_date=row["REMOVED_DATE"] if row["REMOVED_DATE"] else timezone.now(),
                    user=user,
                )
            except lifecycle.IllegalTransition:
                raise ValidationError(
                    f"[Row {idx}] Device cannot be removed (already removed or not in a removable state): "
                    f"{EDV_ID=}, {SAP_ID=}."
                )
            except KeyError as key_error:
                raise KeyError(f"KeyError {key_error} for {device}")

            report.add(
                row=idx,
                identifier=identifier,
                outcome=Outcome.REMOVED,
                detail=f"new REMOVED record: {record.pk}",
            )

    return report
