# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Imports in the journal: one entry per stored outcome, naming whoever ran it."""

from pathlib import Path

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone, translation

from dlcdb.accounts.models import CustomUser
from dlcdb.dataexchange.importer import run_device_import
from dlcdb.dataexchange.models import ImporterList
from dlcdb.journal.models import JournalEntry

from .test_frontend_import import _upload_file

TEST_DATA_DIR = Path("dlcdb/dataexchange/tests/test_data")
INTCSV = ImporterList.ImportFormatChoices.INTERNALCSV
Level = JournalEntry.Level


@pytest.fixture
def importer(db):
    return CustomUser.objects.create(username="importer", email="importer@example.com")


def _run(csv_name, *, tenant, user, importer_list=None, write):
    with translation.override("en"), open(TEST_DATA_DIR / csv_name, "rb") as csv_file:
        return run_device_import(
            file=csv_file,
            tenant=tenant,
            import_format=INTCSV,
            user=user,
            importer_list=importer_list,
            write=write,
        )


def _importer_list(tenant):
    return ImporterList.objects.create(file="imported_csv/pytest.csv", tenant=tenant)


@pytest.mark.django_db
def test_written_import_adds_one_entry(tenant, importer):
    importer_list = _importer_list(tenant)

    _run("devices.correct.csv", tenant=tenant, user=importer, importer_list=importer_list, write=True)

    entry = JournalEntry.objects.get()
    importer_list.refresh_from_db()
    assert entry.source == "dataexchange.import"
    assert entry.event == "imported"
    assert entry.level == Level.SUCCESS
    assert entry.summary == importer_list.summary
    assert entry.body == importer_list.messages
    assert entry.user == importer
    assert entry.tenant == tenant
    assert entry.content_object == importer_list


@pytest.mark.django_db
def test_dry_run_with_bad_rows_adds_a_failed_entry_without_row_warnings(tenant, importer):
    importer_list = _importer_list(tenant)

    _run("devices.rowerrors.csv", tenant=tenant, user=importer, importer_list=importer_list, write=False)

    entry = JournalEntry.objects.get()
    assert entry.event == "dry_run_failed"
    assert entry.level == Level.ERROR
    # The per-row warnings the importer logs are not journaled a second time.
    assert not JournalEntry.objects.filter(event="log").exists()


@pytest.mark.django_db
def test_clean_dry_run_adds_nothing(tenant, importer):
    _run("devices.correct.csv", tenant=tenant, user=importer, importer_list=_importer_list(tenant), write=False)

    assert not JournalEntry.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(("write", "event"), [(False, "dry_run_failed"), (True, "failed")])
def test_raising_import_adds_an_error_entry(tenant, importer, write, event):
    importer_list = _importer_list(tenant)

    with pytest.raises(ValidationError):
        _run("devices.incompleterowheader.csv", tenant=tenant, user=importer, importer_list=importer_list, write=write)

    entry = JournalEntry.objects.get()
    assert entry.event == event
    assert entry.level == Level.ERROR
    assert "Missing column(s):" in entry.body


@pytest.mark.django_db
def test_import_without_log_row_adds_nothing(tenant, importer):
    # The admin form's dry run passes no ImporterList: nothing is stored, nothing journaled.
    _run("devices.rowerrors.csv", tenant=tenant, user=importer, write=False)

    assert not JournalEntry.objects.filter(source="dataexchange.import").exists()


@pytest.mark.django_db
def test_confirm_is_journaled_as_the_confirming_user(client, tenant, plain_static, media_root):
    group = Group.objects.create(name="Importers")
    tenant.groups.add(group)
    uploader, confirmer = (
        CustomUser.objects.create_superuser(email=f"{name}@example.com", password="secret", username=name)
        for name in ("uploader", "confirmer")
    )
    for user in (uploader, confirmer):
        user.groups.add(group)

    client.force_login(uploader)
    client.post(
        reverse("dataexchange:device_import"), {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk}
    )
    importer_list = ImporterList.objects.get()
    client.force_login(confirmer)
    client.post(reverse("dataexchange:device_import_confirm", args=[importer_list.pk]))

    importer_list.refresh_from_db()
    entry = JournalEntry.objects.get(event="imported")
    assert importer_list.user == uploader
    assert entry.user == confirmer


@pytest.mark.django_db
def test_import_links_its_detail_page(tenant):
    importer_list = _importer_list(tenant)

    assert importer_list.get_absolute_url() == reverse("dataexchange:importer_detail", args=[importer_list.pk])


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


@pytest.mark.django_db(transaction=True)
def test_copy_migration_journals_existing_import_logs():
    old_apps = _migrate([("dataexchange", "0008_importerlist_tenant_protect"), ("journal", "0001_initial")])
    Tenant = old_apps.get_model("tenants", "Tenant")
    OldImporterList = old_apps.get_model("dataexchange", "ImporterList")
    tenant = Tenant.objects.create(name="MigTenant")

    def old_import(name, status, messages):
        return OldImporterList.objects.create(
            file=f"imported_csv/{name}.csv",
            import_format="INTCSV",
            tenant=tenant,
            status=status,
            summary=f"summary of {name}",
            messages=messages,
            username="olduser",
        )

    imported = old_import("imported", "success", "Import 2026-09-01 12:00 — INTCSV\nCreated: 3")
    dry_run = old_import("dry-run", "error", "Import (dry run) 2026-09-02 12:00 — INTCSV\nError: 1")
    failed = old_import("failed", "error", "Import failed: Missing column(s): ROOM")
    check_failed = old_import("check-failed", "error", "Import check (dry run) failed: bad header")
    legacy = old_import("legacy", "", "Imported devices: 5")
    old_import("never-confirmed", "", "")

    new_apps = _migrate([("dataexchange", "0009_copy_import_logs_to_journal")])
    NewJournalEntry = new_apps.get_model("journal", "JournalEntry")

    entries = {entry.object_id: entry for entry in NewJournalEntry.objects.all()}
    assert set(entries) == {imported.pk, dry_run.pk, failed.pk, check_failed.pk, legacy.pk}
    assert {pk: (entries[pk].event, entries[pk].level) for pk in entries} == {
        imported.pk: ("imported", Level.SUCCESS),
        dry_run.pk: ("dry_run_failed", Level.ERROR),
        failed.pk: ("failed", Level.ERROR),
        check_failed.pk: ("dry_run_failed", Level.ERROR),
        legacy.pk: ("imported", Level.INFO),
    }
    entry = entries[imported.pk]
    assert entry.source == "dataexchange.import"
    assert entry.summary == "summary of imported"
    assert entry.body == imported.messages
    assert entry.username == "olduser"
    assert entry.tenant_id == tenant.pk
    assert entry.object_repr == "imported_csv/imported.csv"
    assert entry.content_type.model == "importerlist"
    # The row's time, not the migration's.
    assert entry.timestamp == imported.modified_at
    assert entry.timestamp < timezone.now()

    # Leave the schema at head so the test DB stays consistent for other tests.
    executor = MigrationExecutor(connection)
    _migrate(executor.loader.graph.leaf_nodes())
