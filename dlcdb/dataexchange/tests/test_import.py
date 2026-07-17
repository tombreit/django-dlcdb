# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path
import pytest
from django.core.exceptions import ValidationError
from django.utils import translation

from dlcdb.accounts.models import CustomUser
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
from dlcdb.dataexchange.csv_template import build_import_template_csv
from dlcdb.dataexchange.importer import import_data, run_device_import
from dlcdb.dataexchange.models import ImporterList

TEST_DATA_DIR = Path("dlcdb/dataexchange/tests/test_data")


@pytest.fixture(autouse=True)
def import_user(db):
    """
    The importer resolves the audit `user` FK from the passed username via a
    hard lookup, so the importing user must exist. All tests in this module
    import as "pytestuser".
    """
    return CustomUser.objects.create(username="pytestuser")


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
def test_bulk_import_sets_audit_user(tenant, import_user):
    """The importer sets the audit `user` FK (not just the `username` string)."""
    csv_path = TEST_DATA_DIR / "devices.correct.csv"

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

    device = Device.objects.get(edv_id="NTB1282")
    assert device.user == import_user
    assert device.username == "pytestuser"

    record = device.active_record
    assert record.user == import_user
    assert record.username == "pytestuser"

    # A completed loan creates two records (LENT + INROOM); BOTH must carry the
    # audit user/username, not just the last (active) one.
    returned_device = Device.objects.get(edv_id="NTB9002")
    assert returned_device.record_set.count() == 2
    for rec in returned_device.record_set.all():
        assert rec.user == import_user, f"{rec.record_type} record missing audit user"
        assert rec.username == "pytestuser", f"{rec.record_type} record missing username"


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


@pytest.mark.django_db
def test_run_device_import_dry_run_does_not_persist(tenant):
    csv_path = TEST_DATA_DIR / "devices.correct.csv"

    with open(csv_path, "rb") as csv_file:
        report = run_device_import(
            file=csv_file,
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=False,
        )

    assert report.dry_run is True
    assert report.rows
    assert Device.objects.count() == 0


@pytest.mark.django_db
def test_run_device_import_write_persists_report_and_links_devices(tenant):
    csv_path = TEST_DATA_DIR / "devices.correct.csv"
    importer_list = ImporterList.objects.create(file="imported_csv/pytest.csv", tenant=tenant)

    with open(csv_path, "rb") as csv_file:
        report = run_device_import(
            file=csv_file,
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            importer_list=importer_list,
            write=True,
        )

    assert report.dry_run is False

    importer_list.refresh_from_db()
    assert importer_list.status == "success"
    assert importer_list.summary == report.counts_summary()
    assert importer_list.messages

    device = Device.objects.get(edv_id="NTB1282")
    assert device.is_imported is True
    assert device.imported_by == importer_list


def test_build_import_template_csv_contains_all_columns():
    lines = build_import_template_csv().splitlines()
    assert lines[0] == ",".join(ImporterList.VALID_COL_HEADERS)
    # Header plus the two example rows (notebook INROOM, smartphone LENT).
    assert len(lines) == 3


@pytest.mark.django_db
def test_import_template_example_rows_import_cleanly(tenant):
    """The template's example rows must stay valid import data."""
    from io import BytesIO

    report = run_device_import(
        file=BytesIO(build_import_template_csv().encode("utf-8")),
        tenant=tenant,
        import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
        username="pytestuser",
        write=True,
    )

    assert report.level == "success"
    assert len(report.rows) == 2

    notebook = Device.objects.get(edv_id="NTB0001")
    assert notebook.active_record.record_type == Record.INROOM
    assert notebook.active_record.room.number == "101"

    smartphone = Device.objects.get(edv_id="SMA0001")
    assert smartphone.active_record.record_type == Record.LENT
    assert smartphone.active_record.person.email == "ada.lovelace@example.com"


@pytest.mark.django_db
def test_room_without_record_type_defaults_to_inroom(tenant):
    """A row with a ROOM but no RECORD_TYPE gets an INROOM record."""
    import csv
    from io import BytesIO, StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ImporterList.VALID_COL_HEADERS, restval="")
    writer.writeheader()
    writer.writerow({"EDV_ID": "NTB0815", "ROOM": "202"})

    run_device_import(
        file=BytesIO(buffer.getvalue().encode("utf-8")),
        tenant=tenant,
        import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
        username="pytestuser",
        write=True,
    )

    device = Device.objects.get(edv_id="NTB0815")
    assert device.active_record.record_type == Record.INROOM
    assert device.active_record.room.number == "202"


@pytest.mark.django_db
def test_run_device_import_marks_failed_attempt_on_log_row(tenant):
    """A raising import records status "error" on the given ImporterList row."""
    csv_path = TEST_DATA_DIR / "devices.incompleterowheader.csv"
    importer_list = ImporterList.objects.create(file="imported_csv/pytest-failed.csv", tenant=tenant)

    with translation.override("en"):
        with pytest.raises(ValidationError):
            with open(csv_path, "rb") as csv_file:
                run_device_import(
                    file=csv_file,
                    tenant=tenant,
                    import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                    username="pytestuser",
                    importer_list=importer_list,
                    write=False,
                )

    importer_list.refresh_from_db()
    assert importer_list.status == "error"
    assert "Missing column(s):" in importer_list.messages
    assert importer_list.summary
