"""
Copy the existing decommissioning logs into the journal: one entry per
decommissioning file that has a log. From now on the admin writes the journal
entries itself.

Self-contained, as data migrations must be: the subject's text
(``RemoverList.__str__``, the file name) is built here. Decommissioning files
have no tenant, so neither do their entries.

The reverse does nothing: unapplying and reapplying copies the logs again.
"""

from django.db import migrations

SOURCE = "dataexchange.decommission"

# JournalEntry.Level by OperationLogBase.Status. An empty status (older files,
# written before the status existed) says nothing about the outcome: INFO.
LEVELS = {"success": 5, "warning": 4, "error": 3}
INFO = 6


def copy_decommission_logs(apps, schema_editor):
    RemoverList = apps.get_model("dataexchange", "RemoverList")
    JournalEntry = apps.get_model("journal", "JournalEntry")
    ContentType = apps.get_model("contenttypes", "ContentType")

    removals = RemoverList.objects.exclude(messages="").order_by("pk")
    if not removals.exists():
        return
    content_type, _ = ContentType.objects.get_or_create(app_label="dataexchange", model="removerlist")

    JournalEntry.objects.bulk_create(
        (
            JournalEntry(
                timestamp=remover_list.modified_at,
                source=SOURCE,
                event="decommissioned",
                level=LEVELS.get(remover_list.status, INFO),
                summary=remover_list.summary,
                body=remover_list.messages,
                user_id=remover_list.user_id,
                username=remover_list.username,
                content_type=content_type,
                object_id=remover_list.pk,
                object_repr=remover_list.file.name[:200],
            )
            for remover_list in removals.iterator()
        ),
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dataexchange", "0009_copy_import_logs_to_journal"),
    ]

    operations = [
        migrations.RunPython(copy_decommission_logs, migrations.RunPython.noop),
    ]
