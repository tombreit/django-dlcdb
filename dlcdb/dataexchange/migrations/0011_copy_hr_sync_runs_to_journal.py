"""
Copy the stored HR sync runs (the last 50) into the journal, with the rule the
sync follows from now on: a run that left every person unchanged is skipped;
any other run, including one with errors, gets an entry.

Self-contained, as data migrations must be: the subject's text
(``UdbSyncRun.__str__``) is built here. HR sync runs have no tenant and no user.

The reverse does nothing: unapplying and reapplying copies the runs again.
"""

import re

from django.db import migrations

SOURCE = "dataexchange.hr_sync"

# JournalEntry.Level by OperationLogBase.Status.
LEVELS = {"success": 5, "warning": 4, "error": 3}
INFO = 6

# OperationReport.counts_summary() of a run without any notable row.
UNCHANGED_ONLY = re.compile(r"\d+ unchanged|no rows")


def copy_hr_sync_runs(apps, schema_editor):
    UdbSyncRun = apps.get_model("dataexchange", "UdbSyncRun")
    JournalEntry = apps.get_model("journal", "JournalEntry")
    ContentType = apps.get_model("contenttypes", "ContentType")

    runs = [run for run in UdbSyncRun.objects.order_by("pk") if not UNCHANGED_ONLY.fullmatch(run.summary)]
    if not runs:
        return
    content_type, _ = ContentType.objects.get_or_create(app_label="dataexchange", model="udbsyncrun")

    JournalEntry.objects.bulk_create(
        [
            JournalEntry(
                timestamp=run.created_at,
                source=SOURCE,
                # A run-level failure is recorded as the "<sync>" row.
                event="sync_failed" if "<sync>" in run.messages else "synced",
                level=LEVELS.get(run.status, INFO),
                summary=run.summary,
                body=run.messages,
                content_type=content_type,
                object_id=run.pk,
                object_repr=f"HR API Sync Run {run.created_at:%Y-%m-%d %H:%M} ({run.status or 'pending'})",
            )
            for run in runs
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dataexchange", "0010_copy_decommission_logs_to_journal"),
    ]

    operations = [
        migrations.RunPython(copy_hr_sync_runs, migrations.RunPython.noop),
    ]
