# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging
import datetime
from datetime import timedelta

from django.utils import timezone

import huey
from huey.contrib.djhuey import db_periodic_task, db_task, lock_task

from dlcdb.core.models import Device
from .models import Subscription, Message
from .channels import send_via_all_channels
from .intervals import NotificationInterval, INTERVAL_DETAILS

logger = logging.getLogger(__name__)


# Define intervals as a mapping between interval choices and crontab expressions
# Use the cron expressions from the model
# TASK_INTERVALS = {
#     "PENDING_INTERVAL": huey.crontab(minute="*/5"),  # Retry failed messages every 5 minutes
#     **{
#         interval_choice: interval_details["cron_expression"]
#         for interval_choice, interval_details in INTERVAL_DETAILS.items()
#     },
# }


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
    """Update subscription after successful message send"""
    subscription.last_sent = timezone.now()
    subscription.schedule_next_message()
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

    print("Checking for license changes that require subscription updates")

    # Find recently modified devices
    back_in_time_minutes = 60 * 48
    recent_time = timezone.now() - timedelta(minutes=back_in_time_minutes)
    modified_devices = Device.objects.filter(modified_at__gte=recent_time)

    if not modified_devices.exists():
        print("No recently modified devices found")
        return 0

    print(f"Found {modified_devices.count()} recently modified devices")
    update_count = 0

    for device in modified_devices:
        # Get all point-in-time subscriptions for this device
        subscriptions = Subscription.objects.filter(
            device=device, interval=NotificationInterval.POINT_IN_TIME.value, is_active=True
        )
        print(f"{subscriptions=}")

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
                print(
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
        message = Message.objects.select_related("subscription").get(id=message_id)
    except Message.DoesNotExist:
        logger.error(f"Message with ID {message_id} not found")
        return False
    except Exception as e:
        logger.exception(f"Error retrieving message {message_id}: {str(e)}")
        return False

    # Send via all configured channels
    success = send_via_all_channels(message)

    # Update subscription if any channel succeeded
    if success:
        _update_subscription_after_send(message.subscription)

    return success


@db_task()
def queue_messages_for_interval(interval):
    """Create messages for all active subscriptions with the given interval."""

    subscription_count = 0
    message_count = 0

    for subscription in Subscription.objects.filter(interval=interval.value, is_active=True):
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
    """Create a message for a specific subscription if not already created"""
    try:
        subscription = Subscription.objects.get(id=subscription_id)
    except Subscription.DoesNotExist:
        logger.error(f"Subscription with ID {subscription_id} not found")
        return None

    now = timezone.now()

    # Check if the subscription is due for processing
    if subscription.next_scheduled is None or subscription.next_scheduled <= now:
        # Check if a message already exists for this subscription and is not yet sent
        existing_message = Message.objects.filter(
            subscription=subscription, status__in=[Message.STATUS_PENDING, Message.STATUS_SENT]
        ).first()

        if existing_message:
            logger.info(
                f"Skipping subscription {subscription.id}: Existing message {existing_message.id} found with status {existing_message.status}."
            )
            return existing_message.id  # Return existing message ID

        # Create a new message
        message, created = subscription.create_message()

        # Only reschedule for regular intervals, not for POINT_IN_TIME
        if subscription.interval != NotificationInterval.POINT_IN_TIME.value:
            subscription.schedule_next_message()
        else:
            # For point-in-time, just clear the next_scheduled since it's a one-time event
            subscription.next_scheduled = None

        subscription.last_sent = timezone.now()
        subscription.save()

        logger.info(f"Created message {message.id} for subscription {subscription.id}")
        return message.id  # Return new message ID
    else:
        logger.info(
            f"Skipping subscription {subscription.id}: next_scheduled is {subscription.next_scheduled}, which is in the future."
        )
        return None  # Not due for processing


#######################################################################
# @db_periodic_task()
#######################################################################


@db_periodic_task(huey.crontab(minute="*"))  # Run every minute
@lock_task("notification_system_processing")  # Single lock for all notification processing
def process_notification_system():
    """
    Main periodic task that coordinates all notification system processing.
    - Updates license subscriptions based on device changes
    - Processes notification intervals that are due
    """
    print("Starting notification system processing")

    # First update subscriptions for any changed licenses
    update_count = _update_license_subscriptions()
    print(f"Updated {update_count} subscriptions based on device changes")

    # Then process all notification intervals
    _process_all_notification_intervals()

    print("Completed notification system processing")
