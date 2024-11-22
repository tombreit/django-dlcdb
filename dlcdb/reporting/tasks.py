# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging

from django.conf import settings

import huey
from huey.contrib.djhuey import db_periodic_task, lock_task

from .utils.email import build_report_email, send_email
from .utils.process import create_report_if_needed, create_overdue_lenders_emails
from .models import Notification

logger = logging.getLogger(__name__)


def request_notifications(huey_interval=None):
    """
    Check if the notification interval matches the huey interval and create reports.
    """

    for notification in Notification.objects.filter(time_interval=huey_interval):
        if notification.device:
            """
            This is a special notification for a given device (esp. a license).
            Users could have been subscribet to notifications for multiple devices.
            """
            _msg1 = f"Processing device notification: {notification} for device {notification.device}"
            logger.info(_msg1)
            print(f"{_msg1=}")
            # TODO: Implement device notifications, eg. license expires in 30 days.

        else:
            _msg1 = f"Processing notification: {notification}"
            logger.info(_msg1)
            report = create_report_if_needed(notification.pk, caller="huey")

            # Finally sent mail notifications
            if notification.active:
                if notification.notify_no_updates or hasattr(report, "record_collection.records"):
                    email_objs = build_report_email(notification, report.report, report.record_collection)
                    send_email(email_objs)

    # Weekly overdue lending emails. Automatically use EVERY_MINUTE when in dev mode.
    notifiy_overdue_lenders_interval = Notification.EVERY_MINUTE if settings.DEBUG else Notification.WEEKLY
    if all(
        [
            settings.REPORTING_NOTIFY_OVERDUE_LENDERS,
            huey_interval == notifiy_overdue_lenders_interval,
        ]
    ):
        print("Create_overdue_lenders_emails...")
        create_overdue_lenders_emails(caller="huey")


# Periodic tasks.
# https://huey.readthedocs.io/en/latest/guide.html#periodic-tasks

if settings.DEBUG:

    @db_periodic_task(huey.crontab(minute="*/1"))
    @lock_task("reports-minutely-lock")
    def once_a_minute():
        request_notifications(huey_interval=Notification.EVERY_MINUTE)


@db_periodic_task(huey.crontab(hour="0", minute="10", day="*"))
@lock_task("reports-daily-lock")
def daily():
    request_notifications(huey_interval=Notification.DAILY)


@db_periodic_task(huey.crontab(month="*", day="*", day_of_week="1", hour="0", minute="30"))
@lock_task("reports-weekly-lock")
def weekly():
    request_notifications(huey_interval=Notification.WEEKLY)


@db_periodic_task(huey.crontab(month="*", day="1", day_of_week="*", hour="0", minute="50"))
@lock_task("reports-monthly-lock")
def monthly():
    request_notifications(huey_interval=Notification.MONTHLY)


@db_periodic_task(huey.crontab(month="1", day="1", day_of_week="*", hour="0", minute="10"))
@lock_task("reports-yearly-lock")
def yearly():
    request_notifications(huey_interval=Notification.YEARLY)
