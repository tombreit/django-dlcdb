# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
A copyable snapshot of the SQLite database, for file-based backups.

In WAL mode a plain copy of the database file can miss the latest commits,
which sit in the ``-wal`` file until a checkpoint. The snapshot is a complete,
consistent and compacted copy in one file that a backup script can copy at any
time. Compressing it is left to the backup (zstd or gzip shrink it to a tenth).
"""

import os
from pathlib import Path

from django.db import connection as default_connection


def snapshot_path(connection=default_connection):
    """``<database>.snapshot`` next to the database file, or None unless the
    database is an SQLite file (the test database lives in memory)."""
    if connection.vendor != "sqlite" or connection.is_in_memory_db():
        return None
    database = Path(connection.settings_dict["NAME"])
    return database.with_name(f"{database.name}.snapshot")


def write_snapshot(source, path):
    """
    Copy the database behind the sqlite3 connection ``source`` to ``path``.

    ``VACUUM INTO`` reads a consistent state, including what is still in the WAL
    file, while writers carry on. It writes one self-contained file in the
    classic journal mode and leaves out the free pages the live database keeps
    after deletions (38% of production in October 2026). The copy only replaces
    ``path`` once it is complete: a backup copying ``path`` at any moment gets
    the old snapshot or the new one, never a half-written file.
    """
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.unlink(missing_ok=True)  # VACUUM INTO refuses to overwrite a file
    source.execute("VACUUM INTO ?", (str(tmp),))
    os.replace(tmp, path)
