# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Reusable field history for the custom frontend.

``build_field_history`` turns the django-simple-history records of any model
with ``HistoricalRecords()`` into a read-only timeline that answers when, who
and what; ``theme/includes/_field_history.html`` renders it. Pure function, no
template tag, the same convention as ``paginate`` and the filterbar.
"""

import datetime
from dataclasses import dataclass

from django.db.models import Field, ForeignKey, Model
from django.utils.formats import date_format, localize
from django.utils.text import capfirst
from django.utils.timezone import template_localtime
from django.utils.translation import gettext as _
from simple_history.models import DeletedObject, ModelChange

EMPTY = "—"
MASKED = "••••••"

# history_type -> Bootstrap colour of the entry's badge.
ACTION_COLORS = {"+": "success", "~": "secondary", "-": "danger"}


@dataclass(frozen=True)
class FieldChange:
    field: str  # the field's verbose name
    old: str
    new: str


@dataclass(frozen=True)
class HistoryEntry:
    date: datetime.datetime
    user: Model | None  # None: no request (import, task) or a deleted user
    action: str  # Created, Changed or Deleted
    color: str
    reason: str | None
    changes: list[FieldChange]


def build_field_history(obj: Model, *, exclude=(), secret=()) -> list[HistoryEntry]:
    """
    Return the history of ``obj``, newest first, each entry diffed against the
    one before it.

    Fields in ``exclude`` are never shown. Fields in ``secret`` show only
    whether they were set ("—" or a mask), never their value. A *Changed* entry
    with nothing left to show and no change reason is skipped; *Created* and
    *Deleted* are always kept.

    One query: the history user and every tracked foreign key are joined in, as
    ``SimpleHistoryAdmin`` does, because ``diff_against(foreign_keys_are_objs=True)``
    would otherwise fetch each changed related object on its own.
    """
    history = obj.history
    tracked_fields = history.model.tracked_fields
    field_order = {field.name: index for index, field in enumerate(tracked_fields)}
    foreign_keys = [
        field.name for field in tracked_fields if isinstance(field, ForeignKey) and field.name not in exclude
    ]
    records = list(history.select_related("history_user", *foreign_keys))

    entries = []
    for record, older in zip(records, records[1:] + [None]):
        changes = []
        if older is not None:
            delta = record.diff_against(older, excluded_fields=exclude, foreign_keys_are_objs=True)
            changes = [
                _field_change(obj._meta.get_field(change.field), change, secret=change.field in secret)
                for change in sorted(delta.changes, key=lambda change: field_order[change.field])
            ]
        if record.history_type == "~" and not changes and not record.history_change_reason:
            continue
        entries.append(
            HistoryEntry(
                date=record.history_date,
                user=record.history_user,
                action=record.get_history_type_display(),
                color=ACTION_COLORS.get(record.history_type, "secondary"),
                reason=record.history_change_reason,
                changes=changes,
            )
        )
    return entries


def _field_change(field: Field, change: ModelChange, *, secret: bool) -> FieldChange:
    return FieldChange(
        field=capfirst(field.verbose_name),
        old=_display(field, change.old, secret=secret),
        new=_display(field, change.new, secret=secret),
    )


def _display(field: Field, value, *, secret: bool) -> str:
    """One side of a change as text, formatted the way the frontend shows it."""
    # diff_against(foreign_keys_are_objs=True) reports an empty foreign key as
    # DeletedObject(pk=None), not None.
    if isinstance(value, DeletedObject) and value.pk is None:
        value = None
    if value is None or value == "":
        return EMPTY
    if secret:
        return MASKED
    if field.choices:
        return str(dict(field.flatchoices).get(value, value))
    if isinstance(value, bool):
        return _("Yes") if value else _("No")
    if isinstance(value, datetime.datetime):
        return date_format(template_localtime(value), "Y-m-d H:i")
    if isinstance(value, datetime.date):
        return date_format(value, "Y-m-d")
    return str(localize(value))
