# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The task runner's consumer options in ``settings.HUEY``."""

from huey import MemoryHuey
from huey.consumer_options import ConsumerConfig

from dlcdb.settings import base


def test_the_task_runner_clears_task_locks_left_by_an_interrupted_run():
    # The production settings; the test settings replace HUEY with a MemoryHuey.
    huey = MemoryHuey("task-runner-test")
    lock = huey.lock_task("task_import_udb_persons")
    lock.acquire()  # left behind: the run holding it was killed

    # What `run_huey` does with the consumer options of a dict HUEY setting.
    config = ConsumerConfig(**base.HUEY["consumer"])
    huey.create_consumer(**config.values)

    assert not lock.is_locked()
