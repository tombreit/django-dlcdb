# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The copyable SQLite snapshot for file-based backups."""

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from huey.contrib.djhuey import HUEY

from dlcdb.core.tasks import task_sqlite_snapshot
from dlcdb.core.utils.sqlite_snapshot import snapshot_path, write_snapshot


@pytest.fixture
def wal_database(tmp_path):
    """A WAL database whose latest commits are still in the -wal file, with its writer open."""
    path = tmp_path / "db.sqlite3"
    writer = sqlite3.connect(path, isolation_level=None)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("PRAGMA wal_autocheckpoint=0")  # keep every commit in the -wal file
    writer.execute("CREATE TABLE item (name TEXT)")
    writer.executemany("INSERT INTO item VALUES (?)", [(f"item {n}",) for n in range(100)])
    assert (tmp_path / "db.sqlite3-wal").stat().st_size > 0
    yield path, writer
    writer.close()


def _rows(path):
    with sqlite3.connect(path) as reader:
        return reader.execute("SELECT count(*) FROM item").fetchone()[0]


def test_snapshot_contains_the_commits_still_in_the_wal(wal_database):
    path, writer = wal_database
    snapshot = path.with_name("db.sqlite3.snapshot")

    write_snapshot(writer, snapshot)

    assert _rows(snapshot) == 100
    with sqlite3.connect(snapshot) as reader:
        assert reader.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert not snapshot.with_name("db.sqlite3.snapshot.tmp").exists()


def test_snapshot_leaves_out_free_pages(wal_database):
    path, writer = wal_database
    writer.executemany("INSERT INTO item VALUES (?)", [("x" * 1000,) for _ in range(2000)])
    writer.execute("DELETE FROM item WHERE length(name) = 1000")
    writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    assert writer.execute("PRAGMA freelist_count").fetchone()[0] > 0
    snapshot = path.with_name("db.sqlite3.snapshot")

    write_snapshot(writer, snapshot)

    with sqlite3.connect(snapshot) as reader:
        assert reader.execute("PRAGMA freelist_count").fetchone()[0] == 0
    assert snapshot.stat().st_size < path.stat().st_size
    assert _rows(snapshot) == 100


def test_snapshot_replaces_the_previous_one(wal_database):
    path, writer = wal_database
    snapshot = path.with_name("db.sqlite3.snapshot")
    write_snapshot(writer, snapshot)

    writer.execute("INSERT INTO item VALUES ('item 100')")
    snapshot.with_name("db.sqlite3.snapshot.tmp").write_text("left over from an interrupted run")
    write_snapshot(writer, snapshot)

    assert _rows(snapshot) == 101


def test_snapshot_path_is_next_to_an_sqlite_file():
    file_db = SimpleNamespace(
        vendor="sqlite", is_in_memory_db=lambda: False, settings_dict={"NAME": "/srv/dlcdb/data/db/db.sqlite3"}
    )

    assert snapshot_path(file_db) == Path("/srv/dlcdb/data/db/db.sqlite3.snapshot")


def test_no_snapshot_path_without_an_sqlite_file():
    assert snapshot_path(SimpleNamespace(vendor="postgresql")) is None
    assert snapshot_path(SimpleNamespace(vendor="sqlite", is_in_memory_db=lambda: True)) is None


@pytest.mark.django_db
def test_task_skips_the_in_memory_test_database():
    task_sqlite_snapshot.call_local()  # must neither raise nor write anything


def test_task_runs_nightly():
    assert task_sqlite_snapshot.task_class.__name__ in {task.name for task in HUEY._registry.periodic_tasks}
