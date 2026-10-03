"""
Copy the existing mail log into the journal: one entry per sent or failed
notification mail. From now on the email channel writes the entries itself.

Self-contained, as data migrations must be: historical models have no custom
methods, so the recipient (``Message.get_recipients``, ``Person.get_email``)
and the subject's text are built here. Pending mails are skipped: nothing has
happened to them yet.

The reverse does nothing: unapplying and reapplying copies the log again.
"""

from django.db import migrations

SOURCE = "notifications.mail"

# JournalEntry.Level
SUCCESS, ERROR = 5, 3


def _recipient(message):
    if message.recipient_email:
        return message.recipient_email
    subscriber = message.subscription.subscriber
    return (
        subscriber.udb_person_email_internal_business or subscriber.email or subscriber.udb_person_email_private or ""
    )


def _object_repr(message):
    # Message.__str__ names the subscription by its own __str__, which a
    # historical model lacks; its id has to do.
    origin = message.recipient_email or f"subscription {message.subscription_id}"
    return f"{message.pk} - {message.status} - {origin}"[:200]


def copy_mail_log(apps, schema_editor):
    Message = apps.get_model("notifications", "Message")
    JournalEntry = apps.get_model("journal", "JournalEntry")
    ContentType = apps.get_model("contenttypes", "ContentType")

    messages = (
        Message.objects.filter(status__in=["sent", "failed"])
        .select_related("subscription__subscriber", "subscription__device")
        .order_by("pk")
    )
    if not messages.exists():
        return
    content_type, _ = ContentType.objects.get_or_create(app_label="notifications", model="message")

    entries = []
    for message in messages.iterator():
        sent = message.status == "sent"
        outcome = "Mail sent" if sent else "Mail failed"
        if sent:
            body = f"To: {_recipient(message)}" + (f"\nCc: {message.cc_email}" if message.cc_email else "")
        else:
            body = message.error_message
        device = message.subscription.device if message.subscription_id else None
        entries.append(
            JournalEntry(
                timestamp=(message.sent_at or message.modified_at) if sent else message.modified_at,
                source=SOURCE,
                event="sent" if sent else "failed",
                level=SUCCESS if sent else ERROR,
                summary=(f"{outcome}: {message.subject}" if message.subject else outcome)[:255],
                body=body,
                tenant_id=device.tenant_id if device else None,
                content_type=content_type,
                object_id=message.pk,
                object_repr=_object_repr(message),
            )
        )
    JournalEntry.objects.bulk_create(entries, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_message_cc_email"),
        ("journal", "0001_initial"),
        ("core", "0077_alter_device_tenant_protect"),
    ]

    operations = [
        migrations.RunPython(copy_mail_log, migrations.RunPython.noop),
    ]
