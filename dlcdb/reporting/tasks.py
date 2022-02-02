import logging

from django.conf import settings

import huey
from huey.contrib.djhuey import db_periodic_task, lock_task

from .settings import NOTIFY_OVERDUE_LENDERS
from .utils.process import create_report_if_needed, create_overdue_lenders_emails
from .models import Notification

logger = logging.getLogger(__name__)


def request_notifications(huey_interval=None):
    """
    Check if the notification interval matches the huey interval and create reports.
    """

    for notification in Notification.objects.filter(time_interval=huey_interval):
        _msg1 = 'Processing notification: {}'.format(notification)
        logger.info(_msg1)

        create_report_if_needed(notification.pk, caller='huey')

    # Automatically use EVERY_MINUTE when in dev mode
    notifiy_overdue_lenders_interval =  Notification.EVERY_MINUTE if settings.DEBUG else Notification.WEEKLY
    if (huey_interval == notifiy_overdue_lenders_interval) and (NOTIFY_OVERDUE_LENDERS):
        create_overdue_lenders_emails(caller='huey')
   

# Periodic tasks.
# https://huey.readthedocs.io/en/latest/guide.html#periodic-tasks

# if settings.DEBUG:
#     @db_periodic_task(huey.crontab(minute='*'))
#     @lock_task('reports-minutely-lock')
#     def once_a_minute():
#         request_notifications(huey_interval=Notification.EVERY_MINUTE)

@db_periodic_task(huey.crontab(hour='0', minute='10', day='*'))
@lock_task('reports-daily-lock')
def daily():
    request_notifications(huey_interval=Notification.DAILY)

@db_periodic_task(huey.crontab(month='*', day='*', day_of_week='1', hour='0', minute='30'))
@lock_task('reports-weekly-lock')
def weekly():
    request_notifications(huey_interval=Notification.WEEKLY)

@db_periodic_task(huey.crontab(month='*', day='1', day_of_week='*', hour='0', minute='50'))
@lock_task('reports-monthly-lock')
def monthly():
    request_notifications(huey_interval=Notification.MONTHLY)

@db_periodic_task(huey.crontab(month='1', day='1', day_of_week='*', hour='0', minute='10'))
@lock_task('reports-yearly-lock')
def yearly():
    request_notifications(huey_interval=Notification.YEARLY)
