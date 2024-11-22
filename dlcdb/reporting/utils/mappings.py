# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2


def get_admin_url_for_recordtype(recordtype):
    from ...core.models import Record

    url = None

    if recordtype == Record.LENT:
        url = "admin:core_lentrecord_changelist"
    elif recordtype == Record.REMOVED:
        url = "admin:core_removedrecord_changelist"
    else:
        url = "admin:core_record_changelist"

    return url


def get_days_for_interval(interval):
    from ..models import Notification

    days = 1  # default
    if interval == Notification.EVERY_MINUTE:
        days = 1
    elif interval == Notification.DAILY:
        days = 1
    elif interval == Notification.WEEKLY:
        days = 7
    elif interval == Notification.MONTHLY:
        days = 31
    elif interval == Notification.YEARLY:
        days = 365
    return days
