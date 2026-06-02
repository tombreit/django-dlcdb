# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Adopt the existing ``core_importerlist`` / ``core_removerlist`` tables into the
new ``dataexchange`` app *without touching the database*.

The models were moved verbatim out of the ``core`` app. To preserve the existing
rows we register them in this app's migration state pointing at their current
(``core_*``) table names via ``db_table`` and perform no database operations
here. The physical rename to ``dataexchange_*`` happens in ``0002_rename_tables``
once ``core`` has relinquished the models in its own state (``core.0064``).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0003_alter_tenant_options"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="RemoverList",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("file", models.FileField(help_text="Valide Spaltenköpfe: <br>SAP_ID<br>EDV_ID<br>NOTE<br>DISPOSITION_STATE<br>REMOVED_INFO<br>REMOVED_DATE<br>USERNAME", upload_to="toremove_csv", verbose_name="CSV-Datei")),
                        ("note", models.TextField(blank=True, verbose_name="Anmerkung")),
                        ("messages", models.TextField(blank=True, editable=False, verbose_name="DLCDB-Ausgaben zu diesem Vorgang")),
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt")),
                        ("modified_at", models.DateTimeField(auto_now=True, verbose_name="Geändert")),
                    ],
                    options={
                        "verbose_name": "Ausmusterungs-Datei",
                        "verbose_name_plural": "Ausmusterungs-Dateien",
                        "ordering": ["-modified_at", "-created_at"],
                        "db_table": "core_removerlist",
                    },
                ),
                migrations.CreateModel(
                    name="ImporterList",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("file", models.FileField(help_text="Valide Spaltenköpfe: <br>SAP_ID<br>ROOM<br>EDV_ID<br>DEVICE_TYPE<br>SERIAL_NUMBER<br>MANUFACTURER<br>SERIES<br>SUPPLIER<br>PURCHASE_DATE<br>WARRANTY_EXPIRATION_DATE<br>CONTRACT_EXPIRATION_DATE<br>COST_CENTRE<br>BOOK_VALUE<br>NOTE<br>MAC_ADDRESS<br>EXTRA_MAC_ADDRESSES<br>NICK_NAME<br>IS_LENTABLE<br>IS_LICENCE<br>RECORD_TYPE<br>RECORD_NOTE<br>PERSON<br>REMOVED_DATE<br>ORDER_NUMBER", upload_to="imported_csv", verbose_name="CSV-Datei")),
                        ("note", models.TextField(blank=True, null=True, verbose_name="Anmerkung")),
                        ("import_format", models.CharField(choices=[("INTCSV", "Internal (CSV)"), ("SAPCSV", "SAP (CSV)")], default="INTCSV", help_text="Specifiy the format of the import file. Currently officially supported is only 'INTCSV,'.", max_length=10)),
                        ("messages", models.TextField(blank=True, editable=False, verbose_name="DLCDB-Ausgaben zu diesem Import")),
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt")),
                        ("modified_at", models.DateTimeField(auto_now=True, verbose_name="Geändert")),
                        ("tenant", models.ForeignKey(help_text="Import as given tenant.", null=True, on_delete=django.db.models.deletion.SET_NULL, to="tenants.tenant")),
                    ],
                    options={
                        "verbose_name": "Import-Datei",
                        "verbose_name_plural": "Import-Dateien",
                        "ordering": ["-modified_at", "-created_at"],
                        "db_table": "core_importerlist",
                    },
                ),
            ],
        ),
    ]
