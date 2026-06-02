# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Physically rename the adopted tables to the ``dataexchange`` naming scheme:

    core_importerlist  ->  dataexchange_importerlist
    core_removerlist   ->  dataexchange_removerlist

``AlterModelTable(..., table=None)`` resets the table to Django's default
(``<app_label>_<model>``), emitting a single ``ALTER TABLE ... RENAME TO ...``.
The rename preserves all rows; foreign-key constraints referencing the tables
(e.g. ``core_device.imported_by_id``) follow the rename on both PostgreSQL and
SQLite. Reversing this migration restores the ``core_*`` table names.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dataexchange", "0001_initial"),
        ("core", "0064_move_import_models_to_dataexchange"),
    ]

    operations = [
        migrations.AlterModelTable(name="importerlist", table=None),
        migrations.AlterModelTable(name="removerlist", table=None),
    ]
