"""
Drop repeated subscription history rows: keep each subscription's creation, its
deletion and every row that changes a tracked field, remove the rest.

Until 2026-10 the notification scheduler saved licence subscriptions every
minute for 48 hours after a device edit, and each save wrote a full history
row: 1,253,808 rows for 307 subscriptions in production, of which 316 record a
real change. The scheduler's bookkeeping (last_sent, last_run, next_scheduled,
modified_at) is no longer tracked, so it does not count as a change here.

Self-contained, as data migrations must be. The reverse does nothing.
"""

from django.db import migrations

TRACKED = (
    "event",
    "condition",
    "interval",
    "subscriber_id",
    "device_id",
    "subscribed_at",
    "is_active",
    "notify_no_updates",
    "created_at",
)

# SQLite limits the number of query parameters; delete in chunks below it.
CHUNK = 500


def drop_repeated_history(apps, schema_editor):
    History = apps.get_model("notifications", "HistoricalSubscription")

    rows = History.objects.order_by("id", "history_date", "history_id").values_list(
        "history_id", "id", "history_type", "history_change_reason", *TRACKED
    )
    repeated = []
    previous_id = previous_values = None
    for history_id, subscription_id, history_type, reason, *values in rows.iterator(chunk_size=5000):
        # Compared with the row before, which is the last kept one whenever it
        # is a repeat itself.
        if subscription_id == previous_id and history_type == "~" and not reason and values == previous_values:
            repeated.append(history_id)
        previous_id, previous_values = subscription_id, values

    for start in range(0, len(repeated), CHUNK):
        History.objects.filter(history_id__in=repeated[start : start + CHUNK]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_copy_mail_log_to_journal"),
    ]

    operations = [
        migrations.RunPython(drop_repeated_history, migrations.RunPython.noop),
    ]
