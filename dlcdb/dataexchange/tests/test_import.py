# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path
import pytest
from django.core.exceptions import ValidationError
from django.utils import translation

from dlcdb.tenants.models import Tenant
from dlcdb.core.models import (
    InRoomRecord,
    Device,
    Room,
    RemovedRecord,
    Record,
    Person,
    OrganizationalUnit,
)
from dlcdb.dataexchange.importer import import_data
from dlcdb.dataexchange.models import ImporterList

TEST_DATA_DIR = Path("dlcdb/dataexchange/tests/test_data")


@pytest.mark.django_db
def test_bulk_import_csv(tenant):
    csv_path = TEST_DATA_DIR / "devices.correct.csv"

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

    # The CSV contains a LENT row: a LentRecord, the lender Person (matched by a
    # lowercased email) and its OrganizationalUnit must have been created.
    lent_device = Device.objects.get(edv_id="NTB9001")
    lent_record = lent_device.active_record
    assert lent_record.record_type == Record.LENT
    assert lent_record.room.number == "355"
    assert str(lent_record.lent_start_date) == "2024-01-15"
    assert str(lent_record.lent_desired_end_date) == "2024-06-15"
    assert lent_record.lent_end_date is None
    assert lent_record.lent_reason == "Home office"
    assert lent_record.lent_accessories == "Charger, bag"

    person = lent_record.person
    assert person is not None
    # Incoming email "Ada.Lovelace@Example.COM" is normalized to lowercase:
    assert person.email == "ada.lovelace@example.com"
    assert person.first_name == "Ada"
    assert person.last_name == "Lovelace"
    assert person.organizational_unit == OrganizationalUnit.objects.get(name="Mathematics")

    # A completed loan (LENT_END_DATE set) produces two sequential records: the
    # historical LENT record followed by the now-active INROOM record.
    returned_device = Device.objects.get(edv_id="NTB9002")
    assert returned_device.active_record.record_type == Record.INROOM
    assert returned_device.active_record.room.number == "355"

    historical_lent = returned_device.record_set.get(record_type=Record.LENT)
    assert historical_lent.is_active is False
    assert str(historical_lent.lent_end_date) == "2024-04-20"
    assert historical_lent.person.email == "alan.turing@example.com"


@pytest.mark.django_db
def test_get_or_create_person_lowercases_and_dedups():
    from dlcdb.dataexchange.fields import get_or_create_person

    ou = OrganizationalUnit.objects.create(name="Physics")

    person = get_or_create_person(
        first_name="Grace",
        last_name="Hopper",
        email="Grace.Hopper@Example.COM",
        organizational_unit=ou,
    )
    # Email is normalized to lowercase on import:
    assert person.email == "grace.hopper@example.com"

    # A second call with a differently-cased email reuses the same Person:
    same_person = get_or_create_person(
        first_name="Grace",
        last_name="Hopper",
        email="grace.hopper@EXAMPLE.com",
    )
    assert same_person.pk == person.pk
    assert Person.objects.filter(email="grace.hopper@example.com").count() == 1


@pytest.mark.django_db
def test_get_or_create_person_requires_email():
    from dlcdb.dataexchange.fields import get_or_create_person

    with pytest.raises(ValidationError):
        get_or_create_person(first_name="No", last_name="Email", email="")


@pytest.mark.django_db
def test_bulk_import_csv_wrongdate(tenant):
    with pytest.raises(ValueError):
        csv_path = TEST_DATA_DIR / "devices.wrongdateformat.csv"

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
    csv_path = TEST_DATA_DIR / "devices.incompleterowheader.csv"

    # Read the (lazy) message inside the override so it resolves under "en".
    with translation.override("en"):
        with pytest.raises(ValidationError) as excinfo:
            with open(csv_path, "rb") as csv_file:
                import_data(
                    csv_file,
                    importer_inst_pk=None,
                    valid_col_headers=ImporterList.VALID_COL_HEADERS,
                    import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                    tenant=tenant,
                    username="pytestuser",
                    write=True,
                )
        # Friendly, human-readable message (no raw Python set-reprs).
        message = excinfo.value.messages[0]
    assert "Missing column(s):" in message
    assert "{'" not in message


@pytest.mark.django_db
def test_bulk_import_csv_sap(tenant):
    csv_path = TEST_DATA_DIR / "devices-sap.correct.csv"

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
    csv_path = TEST_DATA_DIR / "devices-sap.correct.csv"

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

    # Check that a device in another tenant is not affected by the same device in the import CSV
    new_tenant = Tenant.objects.create(
        name="TestTenant2",
    )
    new_tenant.save()

    device_in_another_tenant = device
    device_in_another_tenant.tenant = new_tenant
    device_in_another_tenant.save()
    device_in_another_tenant_modified_at = device_in_another_tenant.modified_at

    device_in_another_tenant.refresh_from_db()
    assert device_in_another_tenant.tenant == new_tenant

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

    device_in_another_tenant.refresh_from_db()
    assert device_in_another_tenant.modified_at == device_in_another_tenant_modified_at
