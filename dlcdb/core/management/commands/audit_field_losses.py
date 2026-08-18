# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Find device field values that were silently lost on a save, and restore them.

Two form bugs used to clear stored values when a page was saved: a native date
input rendering a localized value (the browser showed an empty field and
submitted it empty) and a field missing from a form layout (never rendered,
therefore never submitted). Both are fixed and guarded by tests, but the values
they already destroyed are only recoverable from the device history.

This walks every revision of every device and reports each field that went from
a value to empty. Read-only unless you ask for a restore.

A loss is not automatically a bug: history cannot tell an accidental wipe from a
field somebody cleared on purpose. Read the report, then restore the rows you
recognise. A value that was re-entered after the loss is never overwritten.

    python manage.py audit_field_losses                            # report everything
    python manage.py audit_field_losses --device 6433              # report one device
    python manage.py audit_field_losses --restore --device 6433    # write that device
    python manage.py audit_field_losses --restore --device 6433 --field purchase_date
    python manage.py audit_field_losses --restore --all            # write every restorable loss
"""

from dataclasses import dataclass, replace
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from simple_history.utils import update_change_reason

from dlcdb.core.models import Device


# Machine-managed or audit columns: a change here is not a user's data going
# missing. `qrcode` matters most -- SIMPLE_HISTORY_FILEFIELD_TO_CHARFIELD stores
# it as a bare filename, which must never be written back into a FileField (and
# Device.save() regenerates it anyway).
EXCLUDED_FIELDS = {
    "id",
    "active_record",
    "qrcode",
    "is_imported",
    "imported_by",
    "user",
    "username",
    "deleted_by",
}


@dataclass(frozen=True)
class FieldLoss:
    """One field that went from a value to empty in a single revision."""

    device_pk: int
    label: str
    field: str
    old_value: object
    lost_at: datetime
    history_id: int
    history_user_id: int | None
    still_empty: bool


def _is_empty(value):
    """Emptiness as a form submits it: a missing value, not a falsy one."""
    return value is None or value == ""


def _skipped_fields():
    """Fields whose emptiness carries no meaning, plus the excluded ones.

    A BooleanField is never "lost": False is a value in its own right and the
    default for every flag on Device.
    """
    booleans = {field.name for field in Device._meta.get_fields() if isinstance(field, models.BooleanField)}
    return EXCLUDED_FIELDS | booleans


def find_field_losses(*, device_pk=None, fields=None):
    """Every field value lost across the device history, oldest loss first.

    Walks the historical table once, in device/revision order, and diffs each
    revision against its predecessor -- the same pairwise ``diff_against`` idiom
    the licenses history view uses, but for the whole table at once.
    """
    skipped = _skipped_fields()
    wanted = set(fields) if fields else None

    historical = Device.history.model.objects.order_by("id", "history_date", "history_id")
    if device_pk is not None:
        historical = historical.filter(id=device_pk)

    current_values = {}
    losses = []
    previous = None

    for revision in historical.iterator():
        if previous is not None and previous.id == revision.id:
            # A deletion snapshot is not an edit, so it cannot lose a value.
            if "-" not in (previous.history_type, revision.history_type):
                delta = revision.diff_against(previous, excluded_fields=EXCLUDED_FIELDS)
                for change in delta.changes:
                    if change.field in skipped or (wanted and change.field not in wanted):
                        continue
                    if _is_empty(change.old) or not _is_empty(change.new):
                        continue
                    losses.append(
                        FieldLoss(
                            device_pk=revision.id,
                            label="",  # filled in below, from the device as it stands now
                            field=change.field,
                            old_value=change.old,
                            lost_at=revision.history_date,
                            history_id=previous.history_id,
                            history_user_id=revision.history_user_id,
                            still_empty=False,  # filled in below, once the latest revision is known
                        )
                    )
        # The last revision seen for a device holds its current values.
        current_values[revision.id] = revision
        previous = revision

    # Both "is it still missing" and "which device is this" are answered by the
    # row as it stands now -- the device's latest revision -- not by the revision
    # that lost the value, whose ids may since have been filled in or changed.
    return [
        replace(
            loss,
            label=_label(current_values[loss.device_pk]),
            still_empty=_is_empty(getattr(current_values[loss.device_pk], loss.field)),
        )
        for loss in losses
    ]


def _label(revision):
    """A device's human handle, from the revision itself (no extra query)."""
    return " / ".join(str(value) for value in (revision.edv_id, revision.sap_id) if value) or f"pk {revision.id}"


def _format(value):
    """Render a lost value for the report: readable, and one line."""
    text = f"'{value}'" if isinstance(value, str) else str(value)
    return text if len(text) <= 30 else f"{text[:29]}…"


class Command(BaseCommand):
    help = "Report device field values that were silently lost on save, and optionally restore them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--device",
            type=int,
            help="Limit to one device (its pk).",
        )
        parser.add_argument(
            "--field",
            action="append",
            dest="fields",
            help="Limit to one field; repeat for several.",
        )
        parser.add_argument(
            "--restore",
            action="store_true",
            help="Write the lost values back. Needs --device or --all.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="restore_all",
            help="With --restore: restore every loss that is still empty.",
        )

    def handle(self, *args, **options):
        device_pk = options["device"]
        fields = options["fields"]
        restore = options["restore"]
        restore_all = options["restore_all"]

        if restore and not (device_pk or restore_all):
            raise CommandError(
                "--restore needs --device <pk> (optionally with --field), or --all to restore "
                "everything at once. Run without --restore first and read the report: a field may "
                "have been cleared on purpose."
            )

        losses = find_field_losses(device_pk=device_pk, fields=fields)
        self._report(losses)

        if not restore:
            if any(loss.still_empty for loss in losses):
                self.stdout.write(
                    self.style.WARNING(
                        "Nothing written. Re-run with --restore --device <pk> [--field <name>], or --restore --all."
                    )
                )
            return

        self._restore(losses)

    def _report(self, losses):
        # The scan yields losses in device order, so a change of pk starts a group.
        reported_pk = None
        for loss in losses:
            if loss.device_pk != reported_pk:
                reported_pk = loss.device_pk
                self.stdout.write(f"device {loss.device_pk} ({loss.label})")
            self.stdout.write(
                f"    {loss.field:26} {_format(loss.old_value):32} lost {loss.lost_at:%Y-%m-%d %H:%M}"
                f"  user {loss.history_user_id or '-'}"
                f"  {'still empty' if loss.still_empty else 're-entered since'}"
            )

        restorable = [loss for loss in losses if loss.still_empty]
        devices = len({loss.device_pk for loss in losses})
        self.stdout.write("")
        self.stdout.write(f"{len(losses)} loss(es) in {devices} device(s), {len(restorable)} still empty.")
        if losses:
            self.stdout.write(
                "Not every loss is a bug -- a field may have been cleared on purpose. Review before restoring."
            )

    def _restore(self, losses):
        restorable = [loss for loss in losses if loss.still_empty]
        skipped = [loss for loss in losses if not loss.still_empty]

        for loss in skipped:
            self.stdout.write(f"  skipped device {loss.device_pk} {loss.field}: a value was re-entered since.")

        if not restorable:
            self.stdout.write(self.style.WARNING("Nothing to restore."))
            return

        self.stdout.write("")
        restored_devices = 0
        with transaction.atomic():
            for device_pk in dict.fromkeys(loss.device_pk for loss in restorable):
                device_losses = [loss for loss in restorable if loss.device_pk == device_pk]
                # Soft-deleted devices are repairable too, as in the other data-fixing commands.
                device = Device.with_softdeleted_objects.get(pk=device_pk)

                for loss in device_losses:
                    setattr(device, loss.field, loss.old_value)
                    self.stdout.write(f"  device {device_pk} {loss.field} -> {loss.old_value!r}")

                changed = [loss.field for loss in device_losses]
                # update_fields keeps Device.save() from touching anything else;
                # modified_at is written on purpose, a restore is a modification.
                device.save(update_fields=[*changed, "modified_at"])
                update_change_reason(
                    device,
                    "Restored {fields} from history entry {history_id} (audit_field_losses)".format(
                        fields=", ".join(changed),
                        history_id=device_losses[0].history_id,
                    ),
                )
                restored_devices += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Restored {len(restorable)} value(s) on {restored_devices} device(s). "
                "Their 'modified_at' moved, so they sort to the top of the device list."
            )
        )
