# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path
import pytest
from django.core.exceptions import ValidationError

from ..utils.bulk_management import import_data
from ..models import ImporterList, InRoomRecord, Device, Room, RemovedRecord


@pytest.mark.django_db
def test_bulk_import_csv(tenant):
    csv_path = Path("dlcdb/core/tests/test_data/devices.correct.csv")

    with open(csv_path, "rb") as csv_file:
        assert import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )


@pytest.mark.django_db
def test_bulk_import_csv_wrongdate(tenant):
    with pytest.raises(ValueError):
        csv_path = Path("dlcdb/core/tests/test_data/devices.wrongdateformat.csv")

        with open(csv_path, "rb") as csv_file:
            assert import_data(
                csv_file,
                importer_inst_pk=None,
                valid_col_headers=ImporterList.VALID_COL_HEADERS,
                import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                tenant=tenant,
                username="pytestuser",
                write=True,
            )


@pytest.mark.django_db
def test_bulk_import_csv_incomplete_rowheader(tenant):
    with pytest.raises(ValidationError):
        csv_path = Path("dlcdb/core/tests/test_data/devices.incompleterowheader.csv")

        with open(csv_path, "rb") as csv_file:
            assert import_data(
                csv_file,
                importer_inst_pk=None,
                valid_col_headers=ImporterList.VALID_COL_HEADERS,
                import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                tenant=tenant,
                username="pytestuser",
                write=True,
            )


@pytest.mark.django_db
def test_bulk_import_csv_sap(tenant):
    csv_path = Path("dlcdb/core/tests/test_data/devices-sap.correct.csv")

    with open(csv_path, "rb") as csv_file:
        assert import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.SAPCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )


@pytest.mark.django_db
def test_bulk_import_csv_sap_update(tenant):
    """
    TODO: DRY the repeated import_data calls and perhaps create the CSV on the fly
    """
    csv_path = Path("dlcdb/core/tests/test_data/devices-sap.correct.csv")

    # Initially import data
    with open(csv_path, "rb") as csv_file:
        assert import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.SAPCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )

    # Fetch a device
    device = Device.objects.all().first()
    old_room = device.active_record.room

    assert device.active_record.room == old_room

    # Directly modify existing database data: New room
    new_room = Room.objects.create(number="900")
    new_record = InRoomRecord(
        device=device,
        room=new_room,
    )
    new_record.save()
    assert device.active_record.room == new_room

    # Update again with the same CSV file
    with open(csv_path, "rb") as csv_file:
        assert import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.SAPCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )

    device.refresh_from_db()
    assert device.active_record.room == old_room

    # Directly modify existing database data: Add devie to be "REMOVED" with next import
    device_to_remove = Device.objects.get(
        sap_id="400003-0",  # This ID must match the device in the CSV file
    )

    # Check the current record: should be "REMOVED" as stated in the CSV
    assert device_to_remove.active_record.record_type == RemovedRecord.REMOVED

    new_record_for_device_to_remove = InRoomRecord(
        device=device_to_remove,
        room=old_room,
    )
    new_record_for_device_to_remove.save()

    assert device_to_remove.active_record.record_type == InRoomRecord.INROOM

    # Update again with the same CSV file: the device should be given a REMOVED record
    with open(csv_path, "rb") as csv_file:
        assert import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.SAPCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )

    device_to_remove.refresh_from_db()
    assert device_to_remove.active_record.record_type == RemovedRecord.REMOVED
