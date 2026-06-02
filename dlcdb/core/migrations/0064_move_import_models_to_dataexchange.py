# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Relinquish the import/decommissioning models from the ``core`` app's migration
state. The ``ImporterList`` / ``RemoverList`` models now live in the
``dataexchange`` app (see ``dataexchange.0001_initial``).

This migration is **state-only**: it redirects the ``Device.imported_by`` /
``HistoricalDevice.imported_by`` foreign keys to ``dataexchange.ImporterList``
and removes the two models from ``core``'s state, without issuing any DDL. The
underlying tables keep their data; they are physically renamed later by
``dataexchange.0002_rename_tables``.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0063_alter_lostrecord_options_alter_removedrecord_options"),
        ("dataexchange", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="device",
                    name="imported_by",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="dataexchange.importerlist",
                        verbose_name="Importiert via",
                    ),
                ),
                migrations.AlterField(
                    model_name="historicaldevice",
                    name="imported_by",
                    field=models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="dataexchange.importerlist",
                        verbose_name="Importiert via",
                    ),
                ),
                migrations.DeleteModel(name="RemoverList"),
                migrations.DeleteModel(name="ImporterList"),
            ],
        ),
    ]
