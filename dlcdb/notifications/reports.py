# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Processing of report subscriptions (Subscriptions with a report event):
select the records matching the subscription's event/condition, create the
report artifact (via the reporting app) and the outgoing Message.
"""

import logging
from collections import namedtuple
from datetime import timedelta

from django.contrib.sites.models import Site
from django.db.models import DateField, ExpressionWrapper, F, Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from dlcdb.core.models import Record
from dlcdb.reporting.services import create_report
from dlcdb.reporting.utils.representations import get_records_as_text

from .email_footer import email_footer_context
from .intervals import NotificationInterval
from .models import Message, Subscription

logger = logging.getLogger(__name__)

# A lending is overdue once lent_desired_end_date + tolerance <= today.
LENT_OVERDUE_TOLERANCE_DAYS = 5

# Reporting window when a subscription has never run before.
FALLBACK_WINDOW_DAYS = {
    NotificationInterval.IMMEDIATELY: 1,
    NotificationInterval.HOURLY: 1,
    NotificationInterval.DAILY: 1,
    NotificationInterval.WEEKLY: 7,
    NotificationInterval.MONTHLY: 31,
    NotificationInterval.YEARLY: 365,
}

ReportRecords = namedtuple("ReportRecords", ["records", "window_start", "window_end"])


def get_admin_url_for_recordtype(recordtype):
    if recordtype == Record.LENT:
        return "admin:core_lentrecord_changelist"
    elif recordtype == Record.REMOVED:
        return "admin:core_removedrecord_changelist"
    return "admin:core_record_changelist"


def get_lent_overdue_records(now):
    """
    All active lent records whose desired end date (plus tolerance) has
    passed. Also used for the overdue lender reminder mails.
    """
    return (
        Record.objects.active_records()
        .filter(record_type=Record.LENT)
        .filter(~Q(lent_desired_end_date__isnull=True) | Q(lent_end_date__isnull=True))
        .annotate(
            lent_desired_end_date_with_tolerance=ExpressionWrapper(
                F("lent_desired_end_date") + timedelta(days=LENT_OVERDUE_TOLERANCE_DAYS),
                output_field=DateField(),
            )
        )
        .filter(lent_desired_end_date_with_tolerance__lte=now)
    )


def get_window_start(subscription, now):
    """
    Start of the reporting window: the subscription's last run, or a
    fallback window for the first run. Also the basis for grouping
    subscriptions with identical settings into one shared report.
    """
    if subscription.last_run:
        return subscription.last_run
    interval = NotificationInterval(subscription.interval)
    return now - timedelta(days=FALLBACK_WINDOW_DAYS[interval])


def get_affected_records(subscription, now):
    """
    Get the records matching a report subscription's event and condition.

    State-based conditions (LENT_IS_OVERDUE, LICENCE_EXPIRES) report the
    current state; all other conditions report records created since the
    last run (or a fallback window for the first run).
    """
    window_start = get_window_start(subscription, now)

    in_window = Q(created_at__gte=window_start, created_at__lte=now)
    records = Record.objects.active_records().filter(record_type=subscription.event)

    condition = subscription.condition
    conditions = Subscription.ConditionChoices

    if condition == conditions.HAS_SAP_ID:
        records = records.filter(in_window).exclude(device__sap_id__isnull=True).exclude(device__sap_id__exact="")
    elif condition == conditions.IS_PC:
        records = records.filter(in_window).filter(device__device_type__prefix="pc")
    elif condition == conditions.IS_NOTEBOOK:
        records = records.filter(in_window).filter(device__device_type__prefix="ntb")
    elif condition == conditions.IS_PC_OR_NOTEBOOK:
        records = records.filter(in_window).filter(
            Q(device__device_type__prefix="pc") | Q(device__device_type__prefix="ntb")
        )
    elif condition == conditions.IS_NEW_PC_OR_NOTEBOOK:
        records = (
            records.filter(in_window)
            .filter(Q(device__device_type__prefix="pc") | Q(device__device_type__prefix="ntb"))
            .exclude(device__edv_id__exact="")
            .exclude(device__serial_number__exact="")
            .exclude(device__mac_address__exact="")
        )
    elif condition == conditions.LENT_IS_OVERDUE:
        records = get_lent_overdue_records(now)
    elif condition == conditions.LICENCE_EXPIRES:
        records = records.filter(device__is_licence=True).filter(device__contract_expiration_date__lte=now)
    else:
        # No condition set: all records of this type in the window.
        records = records.filter(in_window)

    return ReportRecords(records=records, window_start=window_start, window_end=now)


def create_report_messages(subscriptions, *, now=None, update_window=True) -> list[Message]:
    """
    Process a group of report subscriptions that share the same event,
    condition and reporting window (see get_window_start): the record
    selection and the Report artifact are created once and shared, while
    each subscription gets its own outgoing pending Message.

    Returns the created Messages; subscriptions with nothing to report and
    notify_no_updates off get none. With update_window=False (ad-hoc admin
    trigger), the reporting window (last_run) is left untouched.
    """
    now = now or timezone.localtime(timezone.now())
    report_records = get_affected_records(subscriptions[0], now)
    records = report_records.records

    report = None
    record_rows = []
    if records:
        report = create_report(
            records=records,
            event=subscriptions[0].event,
            condition=subscriptions[0].condition,
            window_start=report_records.window_start,
            window_end=now,
        )
        record_rows = get_records_as_text(records=records, event=subscriptions[0].event)

    messages = []
    for subscription in subscriptions:
        if report or subscription.notify_no_updates:
            message = Message.objects.create(
                subscription=subscription,
                report=report,
                subject=report.title if report else f"{subscription}: No records affected",
                body=_render_report_body(subscription, report_records, record_rows),
            )
            logger.info(f"Created message {message.id} for report subscription {subscription.id}")
            messages.append(message)

        if update_window:
            subscription.last_run = now
            subscription.save(update_fields=["last_run", "modified_at"])

    return messages


def create_report_message(subscription, *, now=None, update_window=True) -> Message | None:
    """Process a single report subscription (e.g. the ad-hoc admin trigger)."""
    messages = create_report_messages([subscription], now=now, update_window=update_window)
    return messages[0] if messages else None


def _render_report_body(subscription, report_records, record_rows):
    domain = Site.objects.get_current().domain
    changelist_url = "https://{}{}".format(domain, reverse(get_admin_url_for_recordtype(subscription.event)))
    context = {
        "subscription": subscription,
        "records_count": len(record_rows),
        "record_rows": record_rows,
        "changelist_url": changelist_url,
        "window_start": report_records.window_start,
        "window_end": report_records.window_end,
        **email_footer_context(),
    }
    return render_to_string("notifications/emails/report_body.txt", context)
