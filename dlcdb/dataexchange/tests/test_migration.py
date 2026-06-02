# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Verify that moving ``ImporterList`` / ``RemoverList`` from ``core`` to the
``dataexchange`` app preserves existing data.

The only database-level operation in the whole move is the table rename in
``dataexchange.0002_rename_tables`` (everything else is state-only). This test
exercises exactly that boundary: it rewinds to the state *just before* the
rename (tables still named ``core_*``), seeds rows — including a ``Device``
whose ``imported_by`` FK points at an ``ImporterList`` — then migrates forward
across the rename and asserts every row and the FK survived, and that the
tables now carry the ``dataexchange_*`` names. Finally it checks the rename is
reversible.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


BEFORE_RENAME = [("dataexchange", "0001_initial")]
AFTER_RENAME = [("dataexchange", "0002_rename_tables")]


def _migrate(targets):
    """Migrate to ``targets`` and return the apps registry for the resulting DB state."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


def _table_names():
    return set(connection.introspection.table_names())


@pytest.mark.django_db(transaction=True)
def test_table_move_preserves_data():
    # --- Arrange: rewind to the state just before the physical rename ---
    old_apps = _migrate(BEFORE_RENAME)

    Tenant = old_apps.get_model("tenants", "Tenant")
    ImporterList = old_apps.get_model("dataexchange", "ImporterList")
    RemoverList = old_apps.get_model("dataexchange", "RemoverList")
    Device = old_apps.get_model("core", "Device")

    # Tables still carry their original core_* names at this point.
    assert "core_importerlist" in _table_names()
    assert "core_removerlist" in _table_names()

    tenant = Tenant.objects.create(name="MigTestTenant")
    importer = ImporterList.objects.create(
        file="imported_csv/seed.csv",
        import_format="INTCSV",
        tenant=tenant,
    )
    remover = RemoverList.objects.create(file="toremove_csv/seed.csv")
    device = Device.objects.create(
        edv_id="MIG-DEVICE-1",
        tenant=tenant,
        username="",
        imported_by=importer,
    )

    importer_pk, remover_pk, device_pk = importer.pk, remover.pk, device.pk
    importer_count = ImporterList.objects.count()
    remover_count = RemoverList.objects.count()

    # --- Act: apply the rename ---
    new_apps = _migrate(AFTER_RENAME)

    NewImporterList = new_apps.get_model("dataexchange", "ImporterList")
    NewRemoverList = new_apps.get_model("dataexchange", "RemoverList")
    NewDevice = new_apps.get_model("core", "Device")

    # --- Assert: rows survived under the same PKs ---
    assert NewImporterList.objects.count() == importer_count
    assert NewRemoverList.objects.count() == remover_count
    assert NewImporterList.objects.filter(pk=importer_pk).exists()
    assert NewRemoverList.objects.filter(pk=remover_pk).exists()

    # --- Assert: the Device.imported_by relationship is intact ---
    migrated_device = NewDevice.objects.get(pk=device_pk)
    assert migrated_device.imported_by_id == importer_pk

    # --- Assert: tables now carry the dataexchange_* names ---
    tables = _table_names()
    assert "dataexchange_importerlist" in tables
    assert "dataexchange_removerlist" in tables
    assert "core_importerlist" not in tables
    assert "core_removerlist" not in tables

    # --- Assert: the rename is reversible (data + names restored) ---
    reverted_apps = _migrate(BEFORE_RENAME)
    RevertedImporterList = reverted_apps.get_model("dataexchange", "ImporterList")
    assert "core_importerlist" in _table_names()
    assert "dataexchange_importerlist" not in _table_names()
    assert RevertedImporterList.objects.filter(pk=importer_pk).exists()

    # Leave the schema at head so the test DB stays consistent for other tests.
    _migrate(AFTER_RENAME)
