# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Failed huey tasks into the journal.

Huey logs a failed task itself, but names only the task id ("Unhandled
exception in task <id>."). This receiver logs the task's name instead, through
the ``dlcdb`` logger, so the journal handler picks it up like any other error
and recognizes repeats of the same failure.
"""

import logging

from huey.contrib.djhuey import signal
from huey.signals import SIGNAL_ERROR

logger = logging.getLogger("dlcdb.huey")


@signal(SIGNAL_ERROR)
def log_task_error(signal_name, task, exc=None):
    logger.error("Task %s failed: %s", task.name, exc, exc_info=exc)
