"""
Return the space freed by the subscription history cleanup to the filesystem.

SQLite keeps deleted pages in the file until a VACUUM: without it the production
file would stay at 595 MB instead of about 40 MB. VACUUM cannot run inside a
transaction, hence a non-atomic migration of its own. It rewrites the file once
and needs free disk space about the size of the remaining data; deployments run
migrate while the task runner is stopped. Other databases: nothing to do.
"""

from django.db import migrations


def vacuum(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("VACUUM")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("notifications", "0006_drop_bookkeeping_from_subscription_history"),
    ]

    operations = [
        migrations.RunPython(vacuum, migrations.RunPython.noop, atomic=False),
    ]
