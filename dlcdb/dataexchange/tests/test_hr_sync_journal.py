# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""HR sync runs in the journal: one entry per run in which something happened."""

from unittest import mock

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from dlcdb.dataexchange import udb_sync
from dlcdb.dataexchange.models import UdbSyncRun
from dlcdb.journal.models import JournalEntry

from .test_udb_sync import _contract, _enable_sync, _run_with_payload

Level = JournalEntry.Level

ADA = {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}


@pytest.mark.django_db
def test_run_with_changes_adds_one_entry():
    _enable_sync()

    _run_with_payload(ADA)

    run = UdbSyncRun.objects.get()
    entry = JournalEntry.objects.get()
    assert entry.source == "dataexchange.hr_sync"
    assert entry.event == "synced"
    assert entry.level == Level.SUCCESS
    assert entry.summary == run.summary == "1 created"
    assert entry.body == run.messages
    assert entry.user is None
    assert entry.tenant is None
    assert entry.content_object == run


@pytest.mark.django_db
def test_unchanged_run_adds_nothing():
    _enable_sync()
    _run_with_payload(ADA)

    _run_with_payload(ADA)  # everything unchanged

    assert UdbSyncRun.objects.count() == 2
    assert JournalEntry.objects.count() == 1


@pytest.mark.django_db
def test_run_with_a_failing_contract_is_journaled_every_time():
    _enable_sync()
    payload = {"results": {"contracts": [_contract("uuid-3", "Bad", "Record", drop_checkin=True)]}}

    _run_with_payload(payload)
    _run_with_payload(payload)

    entries = JournalEntry.objects.filter(source="dataexchange.hr_sync")
    assert entries.count() == 2
    assert {(entry.event, entry.level) for entry in entries} == {("synced", Level.ERROR)}
    # The per-contract error line is not journaled a second time as an anomaly.
    assert not JournalEntry.objects.filter(source="dataexchange.udb_sync").exists()


@pytest.mark.django_db
def test_failed_run_adds_a_sync_failed_entry():
    _enable_sync()
    with (
        mock.patch.object(udb_sync, "_fetch_contracts", side_effect=RuntimeError("UDB unreachable")),
        pytest.raises(RuntimeError),
    ):
        udb_sync.import_udb_persons()

    entry = JournalEntry.objects.get()
    assert entry.event == "sync_failed"
    assert entry.level == Level.ERROR
    assert "UDB unreachable" in entry.body


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


@pytest.mark.django_db(transaction=True)
def test_copy_migration_journals_runs_in_which_something_happened():
    old_apps = _migrate([("dataexchange", "0010_copy_decommission_logs_to_journal")])
    OldRun = old_apps.get_model("dataexchange", "UdbSyncRun")

    def run(status, summary, messages="UDB person sync 2026-08-18 06:40 — https://udb.example.org"):
        return OldRun.objects.create(status=status, summary=summary, messages=messages)

    run("success", "257 unchanged")
    run("success", "no rows")
    updated = run("success", "1 updated, 256 unchanged")
    errors = run("error", "256 unchanged, 3 error")
    failed = run("error", "1 error", messages="UDB person sync\n[row 0] <sync>  ERROR (UDB unreachable)")

    new_apps = _migrate([("dataexchange", "0011_copy_hr_sync_runs_to_journal")])
    NewJournalEntry = new_apps.get_model("journal", "JournalEntry")

    entries = {entry.object_id: entry for entry in NewJournalEntry.objects.filter(source="dataexchange.hr_sync")}
    assert {pk: (entries[pk].event, entries[pk].level) for pk in entries} == {
        updated.pk: ("synced", Level.SUCCESS),
        errors.pk: ("synced", Level.ERROR),
        failed.pk: ("sync_failed", Level.ERROR),
    }
    entry = entries[updated.pk]
    assert entry.summary == "1 updated, 256 unchanged"
    assert entry.timestamp == updated.created_at < timezone.now()
    assert entry.object_repr == f"HR API Sync Run {updated.created_at:%Y-%m-%d %H:%M} (success)"
    assert entry.tenant_id is None

    # Leave the schema at head so the test DB stays consistent for other tests.
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
