# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Decommissioning files in the journal: one entry per run, naming who ran it."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Device, Record
from dlcdb.dataexchange.models import RemoverList
from dlcdb.journal.models import JournalEntry

Level = JournalEntry.Level


def _remover_csv(*, edv_id):
    content = f"EDV_ID,SAP_ID,NOTE,DISPOSITION_STATE,REMOVED_INFO,REMOVED_DATE,USERNAME\n{edv_id},,decommissioned,,,,\n"
    return SimpleUploadedFile("remove.csv", content.encode("utf-8"), content_type="text/csv")


@pytest.mark.django_db
def test_admin_decommissioning_adds_one_entry(client, tenant, join_tenant, plain_static, media_root):
    admin = join_tenant(
        CustomUser.objects.create_superuser(email="admin@example.com", password="secret", username="admin")
    )
    client.force_login(admin)
    Device.objects.create(edv_id="REM-1", tenant=tenant)

    response = client.post(
        reverse("admin:dataexchange_removerlist_add"),
        {"file": _remover_csv(edv_id="REM-1"), "note": "old notebooks"},
    )

    assert response.status_code == 302
    remover_list = RemoverList.objects.get()
    assert Device.objects.get(edv_id="REM-1").active_record.record_type == Record.REMOVED
    entry = JournalEntry.objects.get(source="dataexchange.decommission")
    assert entry.event == "decommissioned"
    assert entry.level == Level.SUCCESS
    assert entry.summary == remover_list.summary
    assert entry.body == remover_list.messages
    assert entry.user == admin
    assert entry.tenant is None
    assert entry.content_object == remover_list


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


@pytest.mark.django_db(transaction=True)
def test_copy_migration_journals_existing_decommissioning_logs():
    old_apps = _migrate([("dataexchange", "0009_copy_import_logs_to_journal")])
    OldRemoverList = old_apps.get_model("dataexchange", "RemoverList")
    removed = OldRemoverList.objects.create(
        file="toremove_csv/old.csv",
        status="success",
        summary="2 removed",
        messages="Decommission 2026-09-01 12:00\nRemoved: 2",
        username="olduser",
    )
    legacy = OldRemoverList.objects.create(
        file="toremove_csv/legacy.csv", messages="[I] Starting set_removed_record..."
    )
    OldRemoverList.objects.create(file="toremove_csv/empty.csv")

    new_apps = _migrate([("dataexchange", "0010_copy_decommission_logs_to_journal")])
    NewJournalEntry = new_apps.get_model("journal", "JournalEntry")

    entries = {entry.object_id: entry for entry in NewJournalEntry.objects.filter(source="dataexchange.decommission")}
    assert set(entries) == {removed.pk, legacy.pk}
    entry = entries[removed.pk]
    assert (entry.event, entry.level) == ("decommissioned", Level.SUCCESS)
    assert entry.summary == "2 removed"
    assert entry.body == removed.messages
    assert entry.username == "olduser"
    assert entry.tenant_id is None
    assert entry.object_repr == "toremove_csv/old.csv"
    assert entry.timestamp == removed.modified_at < timezone.now()
    assert entries[legacy.pk].level == Level.INFO

    # Leave the schema at head so the test DB stays consistent for other tests.
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
