# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.utils import translation

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import (
    Device,
    InRoomRecord,
    OrganizationalUnit,
    Person,
    Record,
    RemovedRecord,
    Room,
)
from dlcdb.dataexchange.csv_template import build_import_template_csv
from dlcdb.dataexchange.importer import import_data, run_device_import
from dlcdb.dataexchange.models import ImporterList
from dlcdb.dataexchange.reporting import Outcome
from dlcdb.tenants.models import Tenant

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
    """A bad date is an error *row*, naming the column, the value and the line.

    It used to raise a bare ValueError for the whole file, so the user learned
    that some date somewhere was malformed but not which row or which column.
    """
    csv_path = TEST_DATA_DIR / "devices.wrongdateformat.csv"

    with translation.override("en"), open(csv_path, "rb") as csv_file:
        report = import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            tenant=tenant,
            username="pytestuser",
            write=False,
        )

    errors = [row for row in report.rows if row.outcome is Outcome.ERROR]
    assert len(errors) == 1
    error = errors[0]

    # Line 2 of the file: the header is line 1.
    assert error.row == 2
    assert "NTB1282" in error.identifier
    assert "PURCHASE_DATE" in error.detail
    assert "17.11.2023" in error.detail


@pytest.mark.django_db
def test_bulk_import_csv_wrongdate_writes_nothing(tenant):
    """A write over a file with bad rows is refused outright, not half-applied."""
    csv_path = TEST_DATA_DIR / "devices.wrongdateformat.csv"

    with translation.override("en"):
        with pytest.raises(ValidationError) as excinfo, open(csv_path, "rb") as csv_file:
            import_data(
                csv_file,
                importer_inst_pk=None,
                valid_col_headers=ImporterList.VALID_COL_HEADERS,
                import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                tenant=tenant,
                username="pytestuser",
                write=True,
            )
        assert "Nothing was written" in excinfo.value.messages[0]

    assert Device.objects.count() == 0


@pytest.mark.django_db
def test_bulk_import_csv_incomplete_rowheader(tenant):
    csv_path = TEST_DATA_DIR / "devices.incompleterowheader.csv"

    # Read the (lazy) message inside the override so it resolves under "en".
    with translation.override("en"):
        with pytest.raises(ValidationError) as excinfo, open(csv_path, "rb") as csv_file:
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

    with translation.override("en"), pytest.raises(ValidationError), open(csv_path, "rb") as csv_file:
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


@pytest.mark.django_db
def test_import_report_details_describe_the_records(tenant):
    """Each preview row says which record it writes, not just "created"."""
    import csv
    from io import BytesIO, StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ImporterList.VALID_COL_HEADERS, restval="")
    writer.writeheader()
    writer.writerow({"EDV_ID": "DET0001", "ROOM": "101", "RECORD_TYPE": Record.INROOM})
    writer.writerow(
        {
            "EDV_ID": "DET0002",
            "ROOM": "102",
            "RECORD_TYPE": Record.LENT,
            "LENDER_EMAIL": "ada.lovelace@example.com",
            "LENT_START_DATE": "2024-01-15",
            "LENT_DESIRED_END_DATE": "2024-06-15",
        }
    )
    writer.writerow(
        {
            "EDV_ID": "DET0003",
            "ROOM": "103",
            "RECORD_TYPE": Record.LENT,
            "LENDER_EMAIL": "ada.lovelace@example.com",
            "LENT_START_DATE": "2024-01-15",
            "LENT_DESIRED_END_DATE": "2024-06-15",
            "LENT_END_DATE": "2024-03-01",
        }
    )
    writer.writerow({"EDV_ID": "DET0004", "RECORD_TYPE": Record.REMOVED, "REMOVED_DATE": "2024-05-01"})
    writer.writerow({"EDV_ID": "DET0005", "RECORD_TYPE": Record.LOST})
    writer.writerow({"EDV_ID": "DET0006"})

    with translation.override("en"):
        report = run_device_import(
            file=BytesIO(buffer.getvalue().encode("utf-8")),
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=False,
        )

        assert [row.detail for row in report.rows] == [
            "new device, in room 101",
            "new device, lent to ada.lovelace@example.com (room 102)",
            "new device, lent to ada.lovelace@example.com (room 103), returned",
            "new device, removed on 2024-05-01",
            "new device, not locatable",
            "new device, no record",
        ]


def _dry_run(tenant, filename="devices.rowerrors.csv"):
    """Dry-run a fixture file and return its report."""
    with open(TEST_DATA_DIR / filename, "rb") as csv_file:
        return import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            tenant=tenant,
            username="pytestuser",
            write=False,
        )


def _errors_by_edv_id(report):
    return {
        row.identifier.split()[0].removeprefix("EDV_ID="): row for row in report.rows if row.outcome is Outcome.ERROR
    }


@pytest.mark.django_db
def test_bad_rows_do_not_abort_the_good_ones(tenant):
    """Every problem in the file is reported in one pass.

    The importer used to stop at the first bad row, so a user fixed one line,
    re-uploaded, and discovered the next -- one round trip per broken row.
    """
    with translation.override("en"):
        report = _dry_run(tenant)

    created = [row for row in report.rows if row.outcome is Outcome.CREATED]
    errors = _errors_by_edv_id(report)

    # Four broken rows, all reported together, and the good rows still import.
    assert set(errors) == {"ERR-DATE", "ERR-NOMAIL", "ERR-NOROOM", "ERR-TYPO"}
    assert {row.identifier.split()[0].removeprefix("EDV_ID=") for row in created} == {"ERR-OK-1", "ERR-OK-2"}


@pytest.mark.django_db
def test_row_errors_name_the_line_the_column_and_the_value(tenant):
    """The regression test for the original report: no debugger required.

    Each error must be actionable from the preview alone -- which line of the
    spreadsheet, which device, which column, and what the offending value was.
    """
    with translation.override("en"):
        report = _dry_run(tenant)

    errors = _errors_by_edv_id(report)

    # Line numbers match the spreadsheet: the header is line 1.
    assert errors["ERR-DATE"].row == 3
    assert errors["ERR-NOMAIL"].row == 4
    assert errors["ERR-NOROOM"].row == 5
    assert errors["ERR-TYPO"].row == 6

    # The bad date names its column and quotes the value it could not parse.
    assert "PURCHASE_DATE" in errors["ERR-DATE"].detail
    assert "17.11.2023" in errors["ERR-DATE"].detail

    assert "LENDER_EMAIL" in errors["ERR-NOMAIL"].detail
    assert "ROOM" in errors["ERR-NOROOM"].detail

    # An unknown record type names the bad value *and* the accepted ones.
    typo_detail = errors["ERR-TYPO"].detail
    assert "INROOOM" in typo_detail
    assert "INROOM" in typo_detail and "LENT" in typo_detail


@pytest.mark.django_db
def test_a_file_with_bad_rows_writes_nothing(tenant):
    """Not even the rows that would have imported cleanly."""
    with (
        translation.override("en"),
        pytest.raises(ValidationError),
        open(TEST_DATA_DIR / "devices.rowerrors.csv", "rb") as csv_file,
    ):
        import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )

    assert Device.objects.count() == 0


@pytest.mark.django_db
def test_unknown_record_type_no_longer_creates_a_recordless_device(tenant):
    """ "INROOOM" used to silently produce a device with no record at all."""
    with translation.override("en"):
        report = _dry_run(tenant)

    assert "ERR-TYPO" in _errors_by_edv_id(report)


def _csv_bytes(rows):
    """Build an in-memory internal-format CSV from partial row dicts."""
    import csv as _csv
    from io import BytesIO, StringIO

    buffer = StringIO()
    writer = _csv.DictWriter(buffer, fieldnames=ImporterList.VALID_COL_HEADERS, restval="")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return BytesIO(buffer.getvalue().encode("utf-8"))


@pytest.mark.django_db
def test_lender_name_collision_is_reported_with_the_email(tenant):
    """The original bug report, reproduced: a raw "UNIQUE constraint failed".

    Lenders are resolved by email, but Person also carries a UniqueConstraint on
    lower(first_name) + lower(last_name). A known name arriving under a new email
    therefore fails in the database, and the constraint text names neither the
    person nor the row. The message must name the email and the colliding name.
    """
    Person.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.com")

    lent_row = {
        "EDV_ID": "COLLIDE-1",
        "ROOM": "355",
        "RECORD_TYPE": Record.LENT,
        "LENDER_FIRST_NAME": "Ada",
        "LENDER_LAST_NAME": "Lovelace",
        # Same human, different address -> lookup misses, insert collides.
        "LENDER_EMAIL": "ada.lovelace@example.org",
        "LENT_START_DATE": "2024-01-15",
    }

    with translation.override("en"):
        report = run_device_import(
            file=_csv_bytes([lent_row]),
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=False,
        )

    error = _errors_by_edv_id(report)["COLLIDE-1"]
    assert error.row == 2
    assert "ada.lovelace@example.org" in error.detail
    assert "Ada" in error.detail and "Lovelace" in error.detail


@pytest.mark.django_db
def test_blank_lender_names_collide_and_are_reported(tenant):
    """Two lenders with emails but no names both insert ("", "") -> collision."""
    rows = [
        {
            "EDV_ID": f"BLANK-{index}",
            "ROOM": "355",
            "RECORD_TYPE": Record.LENT,
            "LENDER_EMAIL": f"nameless{index}@example.com",
            "LENT_START_DATE": "2024-01-15",
        }
        for index in (1, 2)
    ]

    with translation.override("en"):
        report = run_device_import(
            file=_csv_bytes(rows),
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=False,
        )

    errors = _errors_by_edv_id(report)
    # The first row is fine; the second one collides and says whose email it was.
    assert "BLANK-2" in errors
    assert "nameless2@example.com" in errors["BLANK-2"].detail
    assert "UNIQUE constraint" not in errors["BLANK-2"].detail.split("Original error:")[0]


@pytest.mark.django_db
def test_duplicate_edv_id_is_reported_against_its_row(tenant):
    """The other route to the reported error: a repeated device id.

    The internal-CSV branch had no duplicate check, so this surfaced as a bare
    "UNIQUE constraint failed: core_device.edv_id" for the whole file.
    """
    rows = [
        {"EDV_ID": "DUPE-1", "ROOM": "355", "RECORD_TYPE": Record.INROOM},
        {"EDV_ID": "DUPE-1", "ROOM": "356", "RECORD_TYPE": Record.INROOM},
    ]

    with translation.override("en"):
        report = run_device_import(
            file=_csv_bytes(rows),
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=False,
        )

    errors = _errors_by_edv_id(report)
    assert "DUPE-1" in errors
    # Line 3 is the duplicate; line 2 imported fine.
    assert errors["DUPE-1"].row == 3
    assert "already exists" in errors["DUPE-1"].detail


@pytest.mark.django_db
def test_soft_deleted_lender_still_imports(tenant):
    """Pins the variant of the report that was already fixed.

    A soft-deleted Person holding the email must be reused and undeleted rather
    than colliding on the unique email.
    """
    person = Person.objects.create(first_name="Alan", last_name="Turing", email="alan@example.com")
    person.delete()  # soft delete

    row = {
        "EDV_ID": "SOFTDEL-1",
        "ROOM": "355",
        "RECORD_TYPE": Record.LENT,
        "LENDER_FIRST_NAME": "Alan",
        "LENDER_LAST_NAME": "Turing",
        "LENDER_EMAIL": "alan@example.com",
        "LENT_START_DATE": "2024-01-15",
    }

    with translation.override("en"):
        report = run_device_import(
            file=_csv_bytes([row]),
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=True,
        )

    assert not _errors_by_edv_id(report)
    assert Device.objects.get(edv_id="SOFTDEL-1").active_record.person.email == "alan@example.com"


@pytest.mark.django_db
def test_ragged_row_is_an_error_row_not_a_crash(tenant):
    """A short data row used to raise AttributeError that nothing caught.

    DictReader fills the missing cells with None, so row["IS_LENTABLE"].lower()
    blew up with no row context and, in the views, an HTTP 500.
    """
    from io import BytesIO

    header = ",".join(ImporterList.VALID_COL_HEADERS)
    # A row that stops after two columns; DictReader fills the rest with None.
    payload = f"{header}\nRAGGED-1,355\n".encode()

    with translation.override("en"):
        report = run_device_import(
            file=BytesIO(payload),
            tenant=tenant,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            username="pytestuser",
            write=False,
        )

    assert [row.outcome for row in report.rows] == [Outcome.ERROR]
    assert report.rows[0].row == 2
