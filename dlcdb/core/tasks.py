import logging
import huey
from django.conf import settings
from huey.contrib.djhuey import db_periodic_task, lock_task

from .utils.udb import import_udb_persons

logger = logging.getLogger(__name__)


# Periodic tasks.
# https://huey.readthedocs.io/en/latest/guide.html#periodic-tasks

if settings.DEBUG:
    @db_periodic_task(huey.crontab(minute='*'))
    @lock_task('get-udb-persones-minutely')
    def once_a_minute():
        logger.info("[huey persons tasks: minutely] Fetch UDB persons...")
        import_udb_persons()

# Run every hour, on the hour:
@db_periodic_task(huey.crontab(minute='0', hour='*/1'))
@lock_task('get-udb-persones-hourly')
def hourly():
    logger.info("[huey persons tasks: hourly] Fetch UDB persons...")
    import_udb_persons()
