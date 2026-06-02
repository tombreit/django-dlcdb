# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the unified import/decommission reporting:

* ``OperationReport`` rendering and severity (no DB), and
* the per-row outcomes produced by the importer (created/updated/skipped) and
  the remover (removed), exercised against the database.
"""

import io
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.utils import translation

from dlcdb.accounts.models import CustomUser
from dlcdb.tenants.models import Tenant
from dlcdb.core.models import Device
from dlcdb.dataexchange.importer import import_data
from dlcdb.dataexchange.remover import set_removed_record
from dlcdb.dataexchange.models import ImporterList
from dlcdb.dataexchange.reporting import Outcome, OperationReport
from dlcdb.dataexchange.validators import validate_column_headers

TEST_DATA_DIR = Path("dlcdb/dataexchange/tests/test_data")


# --- Unit tests for OperationReport (no DB) ---------------------------------


def test_counts_and_level_success():
    report = OperationReport(operation="Import")
    report.add(row=1, identifier="EDV_ID=A", outcome=Outcome.CREATED)
    report.add(row=2, identifier="EDV_ID=B", outcome=Outcome.UPDATED)
    assert report.counts[Outcome.CREATED] == 1
    assert report.counts[Outcome.UPDATED] == 1
    assert report.counts[Outcome.SKIPPED] == 0
    assert report.level == "success"


def test_level_warning_on_skip():
    report = OperationReport(operation="Import")
    report.add(row=1, identifier="EDV_ID=A", outcome=Outcome.CREATED)
    report.add(row=2, identifier="SAP_ID=1-0", outcome=Outcome.SKIPPED, detail="exists in other tenant 'Bar'")
    assert report.level == "warning"


def test_level_error_on_error():
    report = OperationReport(operation="Import")
    report.add(row=1, identifier="EDV_ID=A", outcome=Outcome.ERROR, detail="boom")
    assert report.level == "error"


def test_detailed_and_short_html_content():
    report = OperationReport(operation="Import", context="INTERNALCSV, tenant: Foo")
    report.add(row=1, identifier="EDV_ID=PC-001", outcome=Outcome.CREATED)
    report.add(row=2, identifier="SAP_ID=1-0", outcome=Outcome.SKIPPED, detail="exists in other tenant 'Bar'")

    detailed = report.detailed()
    assert "INTERNALCSV, tenant: Foo" in detailed
    assert "Created: 1" in detailed and "Skipped: 1" in detailed
    assert "[row 1] EDV_ID=PC-001  CREATED" in detailed
    assert "[row 2] SAP_ID=1-0  SKIPPED (exists in other tenant 'Bar')" in detailed

    short = report.short_html()
    assert "1 created" in short and "1 skipped" in short
    assert "See the saved log" in short


def test_short_html_dry_run_prefix():
    report = OperationReport(operation="Import", dry_run=True)
    report.add(row=1, identifier="EDV_ID=A", outcome=Outcome.CREATED)
    assert str(report.short_html()).startswith("Dry run — ")


# --- Importer outcomes (DB) -------------------------------------------------


def _import_sap(csv_file, tenant):
    return import_data(
        csv_file,
        importer_inst_pk=None,
        valid_col_headers=ImporterList.VALID_COL_HEADERS,
        import_format=ImporterList.ImportFormatChoices.SAPCSV,
        tenant=tenant,
        username="pytestuser",
        write=True,
    )


@pytest.mark.django_db
def test_importer_reports_created_updated_skipped(tenant):
    csv_path = TEST_DATA_DIR / "devices-sap.correct.csv"

    # First import: nothing exists yet -> all created, no skips.
    with open(csv_path, "rb") as csv_file:
        report = _import_sap(csv_file, tenant)
    assert report.counts[Outcome.CREATED] > 0
    assert report.counts[Outcome.SKIPPED] == 0
    assert report.level == "success"

    # Re-import same tenant: devices exist with a record -> updated only.
    with open(csv_path, "rb") as csv_file:
        report = _import_sap(csv_file, tenant)
    assert report.counts[Outcome.UPDATED] > 0
    assert report.counts[Outcome.CREATED] == 0

    # Move one device to another tenant, then re-import as the original tenant:
    # that device's sap_id now lives in another tenant -> reported as SKIPPED.
    other_tenant = Tenant.objects.create(name="OtherTenant")
    moved = Device.objects.exclude(sap_id__isnull=True).first()
    moved.tenant = other_tenant
    moved.save()

    with open(csv_path, "rb") as csv_file:
        report = _import_sap(csv_file, tenant)
    assert report.counts[Outcome.SKIPPED] >= 1
    assert report.level == "warning"
    assert any("other tenant" in row.detail for row in report.rows if row.outcome == Outcome.SKIPPED)


# --- Remover outcomes (DB) --------------------------------------------------


def _remover_csv(*, edv_id):
    content = f"EDV_ID,SAP_ID,NOTE,DISPOSITION_STATE,REMOVED_INFO,REMOVED_DATE,USERNAME\n{edv_id},,decommissioned,,,,\n"
    return io.BytesIO(content.encode("utf-8"))


@pytest.mark.django_db
def test_remover_reports_removed_then_fails_loudly():
    CustomUser.objects.create(username="pytestuser")
    Device.objects.create(edv_id="REM-1")

    report = set_removed_record(_remover_csv(edv_id="REM-1"), username="pytestuser", write=True)
    assert report.counts[Outcome.REMOVED] == 1
    assert report.level == "success"

    # Already removed -> fail loudly (unchanged behavior).
    with pytest.raises(ValidationError):
        set_removed_record(_remover_csv(edv_id="REM-1"), username="pytestuser", write=True)


@pytest.mark.django_db
def test_remover_missing_column_raises_friendly_error():
    CustomUser.objects.create(username="pytestuser")
    Device.objects.create(edv_id="REM-2")

    # CSV is missing the required NOTE/DISPOSITION_STATE/... columns: previously a
    # raw KeyError, now the same friendly ValidationError as the importer.
    bad_csv = io.BytesIO(b"EDV_ID,SAP_ID\nREM-2,\n")
    # Read the (lazy) message inside the override so it resolves under "en".
    with translation.override("en"):
        with pytest.raises(ValidationError) as excinfo:
            set_removed_record(bad_csv, username="pytestuser", write=True)
        message = excinfo.value.messages[0]
    assert "Missing column(s):" in message


# --- Column-header validation message ---------------------------------------


def test_validate_column_headers_friendly_message():
    with translation.override("en"):
        with pytest.raises(ValidationError) as excinfo:
            validate_column_headers(
                current_col_headers=["EDV_ID", "SAP_ID"],
                expected_col_headers=["EDV_ID", "SAP_ID", "NOTE", "ROOM"],
            )
        message = excinfo.value.messages[0]
    assert "Missing column(s):" in message
    # Missing columns are listed sorted and comma-separated, without set-reprs.
    assert "NOTE, ROOM" in message
    assert "{'" not in message


def test_validate_column_headers_message_is_translated():
    # The base string is English; German is provided via gettext (locale/de).
    with translation.override("de"):
        with pytest.raises(ValidationError) as excinfo:
            validate_column_headers(
                current_col_headers=["EDV_ID"],
                expected_col_headers=["EDV_ID", "NOTE"],
            )
        message = excinfo.value.messages[0]
    assert "Fehlende Spalte(n):" in message
    assert "NOTE" in message


def test_validate_column_headers_allows_superset():
    # Extra columns are fine; only a missing expected column is an error.
    validate_column_headers(
        current_col_headers=["EDV_ID", "SAP_ID", "EXTRA"],
        expected_col_headers=["EDV_ID", "SAP_ID"],
    )
