# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging

import huey
from django.db import connection
from huey.contrib.djhuey import db_periodic_task, lock_task

from .utils.sqlite_snapshot import snapshot_path, write_snapshot

logger = logging.getLogger(__name__)


# 00:30 UTC: huey schedules run in UTC. A backup script copies the snapshot
# afterwards; a failure raises and reaches the journal through the huey error
# receiver (dlcdb/journal/signals.py).
@db_periodic_task(huey.crontab(hour=0, minute=30))
@lock_task("task_sqlite_snapshot")
def task_sqlite_snapshot():
    path = snapshot_path()
    if path is None:
        logger.info("No SQLite database file, no snapshot written.")
        return
    connection.ensure_connection()
    write_snapshot(connection.connection, path)
    logger.info("SQLite snapshot written: %s (%d MB)", path, path.stat().st_size // 2**20)
