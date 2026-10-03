# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Anomalies into the journal: the logging handler as wired up in LOGGING."""

import logging
from types import SimpleNamespace

import pytest
from django.db import connection, transaction
from django.test import Client
from django.urls import path

from dlcdb.journal import handlers
from dlcdb.journal.models import JournalEntry
from dlcdb.journal.signals import log_task_error

pytestmark = pytest.mark.django_db

# A child of the "dlcdb" logger, so it goes through LOGGING's journal handler.
logger = logging.getLogger("dlcdb.pytest_journal")


def boom(request):
    raise RuntimeError("view exploded")


urlpatterns = [path("boom/", boom)]


@pytest.fixture
def quiet_handler_errors(monkeypatch):
    """The handler reports its own failures via handleError; keep that off stderr."""
    monkeypatch.setattr(logging, "raiseExceptions", False)


def test_warning_becomes_a_log_entry():
    logger.warning("Disk %s almost full", "/srv")

    entry = JournalEntry.objects.get()
    assert entry.source == "pytest_journal"
    assert entry.event == "log"
    assert entry.level == JournalEntry.Level.WARNING
    assert entry.summary == "Disk /srv almost full"
    assert entry.tenant is None
    # The code location, like journald's CODE_FILE/CODE_LINE/CODE_FUNC.
    assert "test_handlers.py:" in entry.body
    assert "in test_warning_becomes_a_log_entry" in entry.body


def test_exception_carries_its_traceback():
    try:
        raise ValueError("bad value")
    except ValueError:
        logger.exception("Processing failed")

    entry = JournalEntry.objects.get()
    assert entry.event == "exception"
    assert entry.level == JournalEntry.Level.ERROR
    assert "Traceback" in entry.body
    assert "ValueError: bad value" in entry.body


def test_critical_level():
    logger.critical("Out of cheese")

    assert JournalEntry.objects.get().level == JournalEntry.Level.CRITICAL


def test_info_and_opted_out_records_are_not_journaled():
    logger.info("Routine")
    logger.error("Journaled elsewhere", extra={"journal": False})

    assert not JournalEntry.objects.exists()


def test_multiline_message_summary_is_its_first_line():
    logger.warning("First line\nsecond line")

    entry = JournalEntry.objects.get()
    assert entry.summary == "First line"
    assert entry.body.startswith("First line\nsecond line")


def test_repeat_within_the_window_is_journaled_once():
    logger.warning("UDB unreachable")
    logger.warning("UDB unreachable")
    assert JournalEntry.objects.count() == 1

    JournalEntry.objects.update(timestamp=JournalEntry.objects.get().timestamp - handlers.REPEAT_WINDOW)
    logger.warning("UDB unreachable")
    assert JournalEntry.objects.count() == 2


def test_same_text_at_another_level_is_no_repeat():
    logger.warning("Mail server slow")
    logger.error("Mail server slow")

    assert JournalEntry.objects.count() == 2


def test_broken_transaction_is_skipped_without_harm():
    with transaction.atomic():
        transaction.set_rollback(True)
        logger.error("Inside a doomed transaction")  # must neither raise nor query

    assert not JournalEntry.objects.exists()
    # The surrounding transaction still works.
    logger.error("After it")
    assert JournalEntry.objects.count() == 1


def test_failing_insert_does_not_break_the_caller(monkeypatch, quiet_handler_errors):
    def failing_save(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO table_that_does_not_exist VALUES (1)")

    monkeypatch.setattr(JournalEntry, "save", failing_save)

    logger.error("Cannot be written")  # must not raise

    # The savepoint rolled back the failed insert only: the transaction is usable.
    assert JournalEntry.objects.count() == 0


def test_logging_while_writing_does_not_recurse(monkeypatch):
    original_save = JournalEntry.save

    def chatty_save(self, *args, **kwargs):
        logger.warning("Logged from inside the write")
        original_save(self, *args, **kwargs)

    monkeypatch.setattr(JournalEntry, "save", chatty_save)

    logger.warning("Outer")

    assert list(JournalEntry.objects.values_list("summary", flat=True)) == ["Outer"]


@pytest.mark.urls("dlcdb.journal.tests.test_handlers")
def test_unhandled_view_exception_is_journaled_with_user(make_user, plain_static):
    user = make_user()
    client = Client(raise_request_exception=False)
    client.force_login(user)

    response = client.get("/boom/")

    assert response.status_code == 500
    entry = JournalEntry.objects.get(source="django.request")
    assert entry.event == "exception"
    assert entry.level == JournalEntry.Level.ERROR
    assert entry.summary == "Internal Server Error: /boom/"
    assert "RuntimeError: view exploded" in entry.body
    assert entry.user == user


def test_not_found_is_not_journaled(client):
    assert client.get("/no-such-page/").status_code == 404

    assert not JournalEntry.objects.exists()


def test_failed_huey_task_is_journaled_with_its_name():
    from huey.contrib.djhuey import HUEY

    assert log_task_error in HUEY._signal.receivers["error"]
    try:
        raise ConnectionError("UDB down")
    except ConnectionError as exc:
        log_task_error("error", SimpleNamespace(name="task_import_udb_persons"), exc)

    entry = JournalEntry.objects.get()
    assert entry.source == "huey"
    assert entry.summary == "Task task_import_udb_persons failed: UDB down"
    assert "ConnectionError: UDB down" in entry.body


@pytest.mark.django_db(transaction=True)
def test_outside_any_transaction_the_entry_is_committed():
    assert not connection.in_atomic_block

    logger.warning("No transaction around")

    assert JournalEntry.objects.filter(summary="No transaction around").exists()
