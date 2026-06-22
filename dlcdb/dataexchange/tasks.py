# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging

import huey
from huey.contrib.djhuey import db_periodic_task, lock_task

from .udb_sync import import_udb_persons

logger = logging.getLogger(__name__)


# Periodic tasks.
# https://huey.readthedocs.io/en/latest/guide.html#periodic-tasks


@db_periodic_task(huey.crontab(minute="*/10"))
@lock_task("task_import_udb_persons")
def task_import_udb_persons():
    logger.info("[huey persons tasks] Fetch UDB persons...")
    import_udb_persons()
