# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the report artifact generation (xlsx spreadsheets, Report model).
"""

import io
import tempfile

import openpyxl

from django.test import TestCase, override_settings
from django.utils import timezone

from dlcdb.core.models import Device, DeviceType, InRoomRecord, Record
from dlcdb.reporting.services import create_report
from dlcdb.reporting.settings import EXPOSED_FIELDS
from dlcdb.reporting.utils.representations import get_records_as_spreadsheet

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="dlcdb-test-media-")


def create_inroom_records(count):
    device_type, _ = DeviceType.objects.get_or_create(name="Notebook", prefix="ntb")
    for i in range(count):
        device = Device.objects.create(device_type=device_type, edv_id=f"ntb90{i}", sap_id=f"90{i}")
        InRoomRecord.objects.create(device=device)
    return Record.objects.active_records().filter(record_type=Record.INROOM)


class SpreadsheetGenerationTests(TestCase):
    def test_spreadsheet_contains_header_and_data_rows(self):
        records = create_inroom_records(2)

        content = get_records_as_spreadsheet(records=records, title="testsheet", event=Record.INROOM)

        workbook = openpyxl.load_workbook(io.BytesIO(content.read()))
        worksheet = workbook.active
        expected_headers = len([item for item in EXPOSED_FIELDS if Record.INROOM in item["used_for"]])
        header_row = [cell.value for cell in worksheet[3]]
        self.assertEqual(len(header_row), expected_headers)
        # header row + 2 data rows (rows 1, 2 and 4 are blank by design)
        self.assertEqual(worksheet.max_row, 6)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CreateReportTests(TestCase):
    def test_create_report_persists_title_body_and_spreadsheet(self):
        records = create_inroom_records(1)
        now = timezone.localtime(timezone.now())

        report = create_report(
            records=records,
            event=Record.INROOM,
            window_start=now,
            window_end=now,
        )

        self.assertIn("INROOM", report.title)
        self.assertTrue(report.body)
        self.assertTrue(report.spreadsheet.name.endswith(".xlsx"))
        self.assertGreater(report.spreadsheet.size, 0)
