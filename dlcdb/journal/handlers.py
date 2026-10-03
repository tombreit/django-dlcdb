# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Runtime anomalies into the journal, through Python logging.

The warnings and errors the code already logs, unhandled exceptions in views
(``django.request``) and failed huey tasks (``signals.py``) reach the journal
without changes at the call sites. ``LOGGING`` attaches ``JournalHandler``.

``LOGGING`` is applied before the app registry is ready, so this module imports
no models at import time.
"""

import logging
from contextvars import ContextVar
from datetime import timedelta

from django.apps import apps
from django.db import connection, transaction
from django.utils import timezone

from dlcdb.core.utils.helpers import get_denormalized_user

# Set while the handler writes: a log call during the write must not recurse.
_emitting = ContextVar("journal_emitting", default=False)

# An anomaly that repeats within this window is journaled once, like journald's
# rate limiting. The console still shows every occurrence.
REPEAT_WINDOW = timedelta(hours=1)

_formatter = logging.Formatter()


class JournalHandler(logging.Handler):
    """
    Copy log records into the journal.

    Never breaks the caller: the entry is written in a savepoint, skipped when
    the surrounding transaction is already broken, and the handler's own errors
    go to ``handleError`` like any logging handler's. An anomaly logged inside a
    transaction that later rolls back is lost from the journal (not from the
    console).
    """

    def emit(self, record):
        # extra={"journal": False}: the caller journals this fact itself.
        if getattr(record, "journal", True) is False or _emitting.get() or not apps.ready:
            return
        token = _emitting.set(True)
        try:
            if connection.in_atomic_block and transaction.get_rollback():
                return  # a broken transaction: every query would fail
            entry = entry_from_record(record)
            if not is_repeat(entry):
                # A savepoint: a failed insert leaves the caller's transaction intact.
                with transaction.atomic():
                    entry.save()
        except Exception:
            self.handleError(record)
        finally:
            _emitting.reset(token)


def entry_from_record(record):
    """Map a log record to an unsaved journal entry."""
    from .models import JournalEntry

    message = record.getMessage()
    body = [message, f"{record.pathname}:{record.lineno} in {record.funcName}"]
    has_traceback = bool(record.exc_info and record.exc_info[0])
    if has_traceback:
        body.append(_formatter.formatException(record.exc_info))

    # django.request passes the request along; other records have none.
    user = getattr(getattr(record, "request", None), "user", None)
    if user is not None and not user.is_authenticated:
        user = None

    return JournalEntry(
        source=record.name.removeprefix("dlcdb."),
        event="exception" if has_traceback else "log",
        level=_level(record.levelno),
        summary=(message.splitlines() or [""])[0][:255],
        body="\n\n".join(body),
        user=user,
        username=get_denormalized_user(user).username,
    )


def is_repeat(entry):
    """Whether the same anomaly was journaled within ``REPEAT_WINDOW``."""
    from .models import JournalEntry

    return JournalEntry.objects.filter(
        source=entry.source,
        level=entry.level,
        summary=entry.summary,
        timestamp__gte=timezone.now() - REPEAT_WINDOW,
    ).exists()


def _level(levelno):
    from .models import JournalEntry

    if levelno >= logging.CRITICAL:
        return JournalEntry.Level.CRITICAL
    if levelno >= logging.ERROR:
        return JournalEntry.Level.ERROR
    if levelno >= logging.WARNING:
        return JournalEntry.Level.WARNING
    return JournalEntry.Level.INFO
