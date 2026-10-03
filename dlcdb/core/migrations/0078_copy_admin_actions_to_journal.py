"""
Copy the custom admin actions from the admin history (LogEntry) into the
journal: activating and deactivating soft-deletable objects, device note
changes on licence records, and deactivated users. The LogEntry rows stay, as
they feed the admin History tab. From now on the admin writes the journal
entries itself.

The rows are recognized by the exact texts the admin wrote. "Deactivated." for
users was written through gettext; it has no translation, so it was always
stored in English.

Self-contained, as data migrations must be. The reverse does nothing:
unapplying and reapplying copies the actions again.
"""

from django.db import migrations
from django.db.models import Q

# JournalEntry.Level.INFO
INFO = 6


def _entry_texts(log_entry):
    """(source, event, summary, body) for one admin history row."""
    message = log_entry.change_message
    if message == "Deactivated.":
        return "accounts.admin", "deactivated", f"Deactivated user: {log_entry.object_repr}", ""
    if message.startswith("Device note changed."):
        return "core.admin", "device_note_changed", "Device note changed", message
    # "Activated" / "Deactivated"
    model_name = log_entry.content_type.model
    return "core.admin", message.lower(), f"{message} {model_name}: {log_entry.object_repr}", ""


def copy_admin_actions(apps, schema_editor):
    LogEntry = apps.get_model("admin", "LogEntry")
    JournalEntry = apps.get_model("journal", "JournalEntry")
    Device = apps.get_model("core", "Device")

    actions = (
        LogEntry.objects.filter(
            Q(change_message__in=["Activated", "Deactivated"])
            | Q(change_message__startswith="Device note changed.")
            | Q(change_message="Deactivated.", content_type__app_label="accounts", content_type__model="customuser")
        )
        .select_related("content_type", "user")
        .order_by("pk")
    )
    if not actions.exists():
        return

    # Entries about a device carry its tenant, like the live ones.
    device_ids = [
        int(action.object_id)
        for action in actions
        if (action.content_type.app_label, action.content_type.model) == ("core", "device")
    ]
    device_tenants = dict(Device.objects.filter(pk__in=device_ids).values_list("pk", "tenant_id"))

    entries = []
    for action in actions.iterator():
        source, event, summary, body = _entry_texts(action)
        object_id = int(action.object_id)
        is_device = (action.content_type.app_label, action.content_type.model) == ("core", "device")
        entries.append(
            JournalEntry(
                timestamp=action.action_time,
                source=source,
                event=event,
                level=INFO,
                summary=summary[:255],
                body=body,
                user_id=action.user_id,
                # CustomUser.__str__ is the email address.
                username=action.user.email,
                tenant_id=device_tenants.get(object_id) if is_device else None,
                content_type_id=action.content_type_id,
                object_id=object_id,
                object_repr=action.object_repr[:200],
            )
        )
    JournalEntry.objects.bulk_create(entries, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0077_alter_device_tenant_protect"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("journal", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_admin_actions, migrations.RunPython.noop),
    ]
