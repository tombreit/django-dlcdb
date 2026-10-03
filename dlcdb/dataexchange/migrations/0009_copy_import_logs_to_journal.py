"""
Copy the existing import logs into the journal: one entry per import that has a
log. From now on the importer writes the journal entries itself.

Self-contained, as data migrations must be: historical models have no custom
methods, so the subject's text (``ImporterList.__str__``, the file name) is
built here. The event is read from the log text, which the importer writes in
untranslated English.

The reverse does nothing: unapplying and reapplying copies the logs again.
"""

from django.db import migrations

SOURCE = "dataexchange.import"

# JournalEntry.Level by OperationLogBase.Status. An empty status (older imports,
# or a dry run never confirmed) says nothing about the outcome: INFO.
LEVELS = {"success": 5, "warning": 4, "error": 3}
INFO = 6


def _event(messages):
    first_line = messages.splitlines()[0]
    if "(dry run)" in first_line:
        # "Import (dry run) <date> — ..." or "Import check (dry run) failed: ..."
        return "dry_run_failed"
    if first_line.startswith("Import failed:"):
        return "failed"
    return "imported"


def copy_import_logs(apps, schema_editor):
    ImporterList = apps.get_model("dataexchange", "ImporterList")
    JournalEntry = apps.get_model("journal", "JournalEntry")
    ContentType = apps.get_model("contenttypes", "ContentType")

    imports = ImporterList.objects.exclude(messages="").order_by("pk")
    if not imports.exists():
        return
    content_type, _ = ContentType.objects.get_or_create(app_label="dataexchange", model="importerlist")

    JournalEntry.objects.bulk_create(
        (
            JournalEntry(
                # The time of the last stored outcome; the row keeps no other.
                timestamp=importer_list.modified_at,
                source=SOURCE,
                event=_event(importer_list.messages),
                level=LEVELS.get(importer_list.status, INFO),
                summary=importer_list.summary,
                body=importer_list.messages,
                # The uploader: an old row does not know who confirmed it.
                user_id=importer_list.user_id,
                username=importer_list.username,
                tenant_id=importer_list.tenant_id,
                content_type=content_type,
                object_id=importer_list.pk,
                object_repr=importer_list.file.name[:200],
            )
            for importer_list in imports.iterator()
        ),
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dataexchange", "0008_importerlist_tenant_protect"),
        ("journal", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_import_logs, migrations.RunPython.noop),
    ]
