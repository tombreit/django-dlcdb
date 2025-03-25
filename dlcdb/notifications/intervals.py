from django.utils.translation import gettext_lazy as _
import datetime
import huey
from django.conf import settings
from datetime import timedelta

from enum import Enum


class NotificationInterval(Enum):
    POINT_IN_TIME = "point_in_time"  # Add this new option
    IMMEDIATELY = "immediately"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


INTERVAL_DETAILS = {
    NotificationInterval.POINT_IN_TIME: {
        "display_name": _("Specific Date/Time"),
        "cron_expression": huey.crontab(minute="*"),  # Check every minute for due point-in-time notifications
        # For point-in-time, we don't reschedule after sending
        "schedule_function": lambda now: None,
        # For interval start, we use the exact time stored in next_scheduled
        "get_interval_start": lambda now: now,  # This isn't really used for POINT_IN_TIME
    },
    NotificationInterval.IMMEDIATELY: {
        "display_name": _("Immediately"),
        "cron_expression": huey.crontab(minute="*"),  # Every minute
        "schedule_function": lambda now: now,
        "get_interval_start": lambda now: now,  # For immediate, start is just "now"
    },
    NotificationInterval.HOURLY: {
        "display_name": _("Every Hour"),
        "cron_expression": huey.crontab(minute=0),
        "schedule_function": lambda now: now + datetime.timedelta(hours=1),
        "get_interval_start": lambda now: now.replace(minute=0, second=0, microsecond=0),
    },
    NotificationInterval.DAILY: {
        "display_name": _("Every Day"),
        "cron_expression": huey.crontab(hour=7, minute=0),
        "schedule_function": lambda now: now + datetime.timedelta(days=1),
        "get_interval_start": lambda now: now.replace(hour=0, minute=0, second=0, microsecond=0),
    },
    NotificationInterval.WEEKLY: {
        "display_name": _("Every Week"),
        "cron_expression": huey.crontab(day_of_week=1, hour=7, minute=0),
        "schedule_function": lambda now: now + datetime.timedelta(weeks=1),
        "get_interval_start": lambda now: (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        ),
    },
    NotificationInterval.MONTHLY: {
        "display_name": _("Every Month"),
        "cron_expression": huey.crontab(day=1, hour=7, minute=0),
        "schedule_function": lambda now: add_months(now, 1),
        "get_interval_start": lambda now: now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
    },
    NotificationInterval.YEARLY: {
        "display_name": _("Every Year"),
        "cron_expression": huey.crontab(month=1, day=1, hour=7, minute=0),
        "schedule_function": lambda now: add_years(now, 1),
        "get_interval_start": lambda now: now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
    },
}

if settings.DEBUG:
    DEBUG_INTERVALS = {
        NotificationInterval.IMMEDIATELY: {"cron_expression": huey.crontab(minute="*")},
        NotificationInterval.HOURLY: {"cron_expression": huey.crontab(minute="*/2")},
        NotificationInterval.DAILY: {"cron_expression": huey.crontab(minute="*/5")},
        NotificationInterval.WEEKLY: {"cron_expression": huey.crontab(minute="*/10")},
        NotificationInterval.MONTHLY: {"cron_expression": huey.crontab(minute="*/15")},
        NotificationInterval.YEARLY: {"cron_expression": huey.crontab(minute="*/30")},
    }

    for interval, debug_config in DEBUG_INTERVALS.items():
        INTERVAL_DETAILS[interval]["cron_expression"] = debug_config["cron_expression"]


def add_months(source_date, months):
    """Add months to a date"""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(
        source_date.day,
        [
            31,
            29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return datetime.datetime(
        year,
        month,
        day,
        source_date.hour,
        source_date.minute,
        source_date.second,
        source_date.microsecond,
        source_date.tzinfo,
    )


def add_years(source_date, years):
    """Add years to a date"""
    try:
        return source_date.replace(year=source_date.year + years)
    except ValueError:
        # This handles the case of leap years
        return source_date.replace(year=source_date.year + years, month=2, day=28)
