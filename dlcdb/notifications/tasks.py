# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging
import datetime
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

import huey
from huey.contrib.djhuey import db_periodic_task, db_task, lock_task

from dlcdb.core.models import Device
from .models import Subscription, Message
from .channels import send_via_all_channels
from .intervals import NotificationInterval, INTERVAL_DETAILS
from .overdue_lenders import create_overdue_lender_messages
from .reports import create_report_message, create_report_messages, get_window_start

logger = logging.getLogger(__name__)


#######################################################################
# task utilities
#######################################################################


def _ensure_aware_dt(dt):
    """Ensure datetime is timezone-aware"""
    if dt is None:
        return None

    # If it's a date object, convert it to datetime at midnight
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        dt = datetime.datetime.combine(dt, datetime.time.min)

    # Now make it timezone-aware if needed
    if not timezone.is_aware(dt):
        dt = timezone.make_aware(dt)

    return dt


def _update_subscription_after_send(subscription):
    """Record a successful send. Rescheduling happens at message creation."""
    subscription.last_sent = timezone.now()
    subscription.save()


def _process_messages_for_interval(interval):
    """
    Process all pending messages for a specific interval.
    Ensures emails are sent only once per interval period.
    """
    now = timezone.now()

    # Get the interval start time using our centralized function
    try:
        interval_start = INTERVAL_DETAILS[interval]["get_interval_start"](now)
    except KeyError:
        logger.error(f"Unknown interval: {interval}")
        return

    # Get pending or failed messages for this interval that haven't been processed in this interval period
    pending_messages = Message.objects.filter(
        subscription__interval=interval.value,
        status__in=[Message.STATUS_PENDING, Message.STATUS_FAILED],
    )

    # For non-immediate intervals, only process messages at the start of the interval
    # This ensures emails are sent exactly once at the beginning of each interval
    if interval != NotificationInterval.IMMEDIATELY:
        # Only process if we're within the first minute of the interval
        current_minute = now.replace(second=0, microsecond=0)
        if current_minute != interval_start.replace(second=0, microsecond=0):
            logger.info(f"Not at the beginning of {interval.value} interval. Skipping message processing.")
            return

    message_count = 0
    for message in pending_messages:
        # Send the message
        message_id = message.id
        logger.info(f"Processing {interval.value} message {message_id}")
        send_message(message_id)
        message_count += 1

    if message_count > 0:
        logger.info(f"Processed {message_count} messages for {interval.value} interval")
    else:
        logger.info(f"No messages to process for {interval.value} interval")


def _process_all_notification_intervals():
    """
    Process all intervals that are due based on the current time.
    This replaces the individual interval-specific tasks.
    """
    now = timezone.now()

    for interval in NotificationInterval:
        interval_start = INTERVAL_DETAILS[interval]["get_interval_start"](now)

        # Determine if this interval is due for processing
        should_process = False
        if interval == NotificationInterval.IMMEDIATELY:
            # Always process immediate notifications
            should_process = True
        else:
            # For other intervals, only process at the beginning of the interval
            current_minute = now.replace(second=0, microsecond=0)
            interval_minute = interval_start.replace(second=0, microsecond=0)

            # If we're at the start of an interval (first minute), process it
            if current_minute == interval_minute:
                should_process = True

        if should_process:
            logger.info(f"Processing {interval.value} interval")
            queue_messages_for_interval(interval)
            _process_messages_for_interval(interval)
        else:
            logger.debug(f"Skipping {interval.value} interval - not at interval start")


def _update_license_subscriptions():
    """
    Check for device/license changes and update related subscriptions.
    Monitors fields like contract_expiration_date and updates subscriptions accordingly.
    """

    logger.info("Checking for license changes that require subscription updates")

    # Find recently modified devices
    back_in_time_minutes = 60 * 48
    recent_time = timezone.now() - timedelta(minutes=back_in_time_minutes)
    modified_devices = Device.objects.filter(modified_at__gte=recent_time)

    if not modified_devices.exists():
        logger.info("No recently modified devices found")
        return 0

    logger.info(f"Found {modified_devices.count()} recently modified devices")
    update_count = 0

    for device in modified_devices:
        # Get all point-in-time subscriptions for this device
        subscriptions = Subscription.objects.filter(
            device=device, interval=NotificationInterval.POINT_IN_TIME.value, is_active=True
        )
        if not subscriptions.exists():
            continue

        # Update each subscription based on its event type
        for subscription in subscriptions:
            updated = False

            # For CONTRACT_EXPIRES_SOON, set to 30 days before expiration
            if (
                subscription.event == Subscription.NotificationEventChoices.CONTRACT_EXPIRES_SOON
                and device.contract_expiration_date
            ):
                expiration_date = _ensure_aware_dt(device.contract_expiration_date)
                if expiration_date:  # Only proceed if not None
                    notify_date = expiration_date - timedelta(days=30)
                    subscription.schedule_next_message(datetime_obj=notify_date)
                    updated = True

            # For CONTRACT_EXPIRED, set to expiration date
            elif (
                subscription.event == Subscription.NotificationEventChoices.CONTRACT_EXPIRED
                and device.contract_expiration_date
            ):
                expiration_date = _ensure_aware_dt(device.contract_expiration_date)
                if expiration_date:  # Only proceed if not None
                    subscription.schedule_next_message(datetime_obj=expiration_date)
                    updated = True

            # Save if updated
            if updated:
                subscription.save()
                update_count += 1
                logger.info(
                    f"Updated subscription {subscription.id} for device {device.id}, "
                    f"event {subscription.event}, next_scheduled={subscription.next_scheduled}"
                )

                # Update any existing pending messages
                messages = Message.objects.filter(subscription=subscription, status=Message.STATUS_PENDING)
                for message in messages:
                    message.generate_content(force=True)
                    logger.info(f"Updated content for message {message.id}")

    logger.info(f"Updated {update_count} subscriptions based on device changes")
    return update_count


#######################################################################
# @db_task()
#######################################################################


@db_task()
def send_message(message_id):
    """Send a message by ID via the appropriate channel(s)"""
    try:
        message = Message.objects.select_related("subscription", "subscription__subscriber", "report").get(
            id=message_id
        )
    except Message.DoesNotExist:
        logger.error(f"Message with ID {message_id} not found")
        return False
    except Exception as e:
        logger.exception(f"Error retrieving message {message_id}: {str(e)}")
        return False

    # Send via all configured channels
    success = send_via_all_channels(message)

    # Record the send on the subscription; standalone messages have none.
    if success and message.subscription is not None:
        _update_subscription_after_send(message.subscription)

    return success


@db_task()
def queue_messages_for_interval(interval):
    """Create messages for all active subscriptions with the given interval."""

    subscription_count = 0
    message_count = 0
    now = timezone.localtime(timezone.now())

    # Report subscriptions: subscribers may hold identical subscriptions
    # (uniqueness is only enforced per subscriber), so group the due ones by
    # settings and reporting window and build each report only once. Due
    # means: scheduled, and the scheduled time has passed (report
    # subscriptions are never POINT_IN_TIME, see Subscription.clean).
    due_report_subscriptions = Subscription.objects.filter(
        interval=interval.value,
        is_active=True,
        event__in=Subscription.REPORT_EVENTS,
        next_scheduled__isnull=False,
        next_scheduled__lte=now,
    )
    groups = {}
    for subscription in due_report_subscriptions:
        key = (subscription.event, subscription.condition, get_window_start(subscription, now))
        groups.setdefault(key, []).append(subscription)

    for group in groups.values():
        messages = create_report_messages(group, now=now)
        subscription_count += len(group)
        message_count += len(messages)
        for subscription in group:
            subscription.schedule_next_message()
            subscription.save()

    for subscription in Subscription.objects.filter(interval=interval.value, is_active=True).exclude(
        event__in=Subscription.REPORT_EVENTS
    ):
        result = queue_message(subscription.id)
        subscription_count += 1
        if result:  # If a message ID was returned
            message_count += 1

    logger.info(
        f"Processed {subscription_count} subscriptions, created {message_count} new messages for {interval.value} interval"
    )
    return message_count


@db_task()
def queue_message(subscription_id):
    """Create a message for a specific subscription if it is due."""
    try:
        subscription = Subscription.objects.get(id=subscription_id)
    except Subscription.DoesNotExist:
        logger.error(f"Subscription with ID {subscription_id} not found")
        return None

    now = timezone.now()

    # Due means: scheduled, and the scheduled time has passed. No schedule
    # (e.g. a fired one-shot, or a point-in-time date not yet known) means
    # not due.
    if subscription.next_scheduled is None or subscription.next_scheduled > now:
        logger.info(f"Skipping subscription {subscription.id}: not due (next_scheduled={subscription.next_scheduled})")
        return None

    if subscription.is_report_subscription:
        # Every scheduled run produces a fresh report message (or none, when
        # nothing matched and notify_no_updates is off).
        message = create_report_message(subscription)
    else:
        # Reuse an unsent message instead of queueing a duplicate. One-shots
        # (POINT_IN_TIME) fire once, ever: their sent message keeps blocking,
        # since _update_license_subscriptions may re-arm next_scheduled on
        # any device edit.
        blocking_statuses = [Message.STATUS_PENDING, Message.STATUS_FAILED]
        if subscription.interval == NotificationInterval.POINT_IN_TIME.value:
            blocking_statuses.append(Message.STATUS_SENT)
        existing_message = Message.objects.filter(subscription=subscription, status__in=blocking_statuses).first()
        if existing_message:
            logger.info(
                f"Skipping subscription {subscription.id}: unsent message {existing_message.id} "
                f"({existing_message.status}) exists."
            )
            return existing_message.id
        message, _ = subscription.create_message()

    # Only reschedule for regular intervals, not for POINT_IN_TIME
    if subscription.interval != NotificationInterval.POINT_IN_TIME.value:
        subscription.schedule_next_message()
    else:
        # For point-in-time, just clear the next_scheduled since it's a one-time event
        subscription.next_scheduled = None
    subscription.save()

    if message:
        logger.info(f"Created message {message.id} for subscription {subscription.id}")
        return message.id
    return None


#######################################################################
# @db_periodic_task()
#######################################################################


@db_periodic_task(
    # Weekly on Monday mornings; every 10 minutes in development.
    huey.crontab(minute="*/10") if settings.DEBUG else huey.crontab(day_of_week=1, hour=7, minute=5)
)
@lock_task("notify_overdue_lenders")
def notify_overdue_lenders():
    """Send reminder mails to lenders with overdue lendings."""
    if not settings.NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS:
        return

    for message in create_overdue_lender_messages():
        send_message(message.id)


@db_periodic_task(huey.crontab(minute="*"))  # Run every minute
@lock_task("notification_system_processing")  # Single lock for all notification processing
def process_notification_system():
    """
    Main periodic task that coordinates all notification system processing.
    - Updates license subscriptions based on device changes
    - Processes notification intervals that are due
    """
    logger.info("Starting notification system processing")

    # First update subscriptions for any changed licenses
    _update_license_subscriptions()

    # Then process all notification intervals
    _process_all_notification_intervals()

    logger.info("Completed notification system processing")
