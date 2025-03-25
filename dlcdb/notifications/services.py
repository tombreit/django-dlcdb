import logging
from django.utils import timezone

from .models import Subscription, Message
from .intervals import NotificationInterval

logger = logging.getLogger(__name__)

# PUBLIC API - exposed to other apps


def create_license_subscriptions(
    subscriber, device, interval=NotificationInterval.IMMEDIATELY.value, scheduled_times=None
):
    """
    Create subscriptions for all license events for a specific subscriber and device.

    Args:
        subscriber: Person instance who will receive notifications
        device: Device instance the notifications are about
        interval: Notification interval for regular subscriptions
        scheduled_times: Dict mapping event types to specific datetimes
                         e.g. {'CONTRACT_EXPIRED': expires_at_datetime}
    """
    result = []
    scheduled_times = scheduled_times or {}

    print(f"create_license_subscriptions {subscriber=}, {device=}/{type(device)=}, {interval=}, {scheduled_times=}")

    for license_event in Subscription.LICENSE_EVENTS:
        print(f"create_license_subscriptions {license_event=}")
        # Determine which interval to use
        sub_interval = interval
        if license_event in scheduled_times:
            sub_interval = NotificationInterval.POINT_IN_TIME.value

        subscription, created = Subscription.objects.get_or_create(
            event=license_event, subscriber=subscriber, device=device, defaults={"interval": sub_interval}
        )

        # Set scheduled time
        if license_event in scheduled_times:
            # For point-in-time, directly set next_scheduled without calling schedule_next_message
            subscription.next_scheduled = scheduled_times[license_event]
            subscription.save()
        elif created:
            # For regular intervals, use schedule_next_message
            subscription.schedule_next_message()
            subscription.save()

        result.append(
            {
                "subscription": subscription,
                "created": created,
            }
        )

        print(
            f"{'Created' if created else 'Updated'} subscription {subscription.id} "
            f"for {subscriber} on device {device.id}, event {license_event}"
        )

    return result


def delete_license_subscriptions(subscriber, device):
    """
    Delete all license event subscriptions for a specific subscriber and device.

    Args:
        subscriber: Person instance
        device: Device instance

    Returns:
        List of dictionaries with deletion results
    """
    result = []

    for license_event in Subscription.LICENSE_EVENTS:
        deleted_count, deleted_objects = Subscription.objects.filter(
            event=license_event,
            subscriber=subscriber,
            device=device,
        ).delete()

        result.append(
            {
                "event": license_event,
                "deleted_count": deleted_count,
            }
        )

        logger.info(
            f"Deleted {deleted_count} subscriptions for {subscriber} on device {device.id}, event {license_event}"
        )

    return result


def get_pending_messages_for_subscriber(subscriber, include_failed=True):
    """
    Get all pending messages for a subscriber.

    Args:
        subscriber: Person instance
        include_failed: Whether to include failed messages

    Returns:
        QuerySet of Message instances
    """
    status_list = [Message.STATUS_PENDING]
    if include_failed:
        status_list.append(Message.STATUS_FAILED)

    return Message.objects.filter(subscription__subscriber=subscriber, status__in=status_list).order_by("created_at")


# PRIVATE API - for internal use only


def _trigger_license_event(device, event_type, scheduled_time=None):
    """
    INTERNAL: Process notifications for a license-related event.

    Args:
        device: Device instance
        event_type: One of Subscription.LICENSE_EVENTS
        scheduled_time: When the notification should be sent

    Returns:
        Number of messages queued or created
    """
    if event_type not in Subscription.LICENSE_EVENTS:
        logger.warning(f"Event type {event_type} is not a license event")
        return 0

    subscriptions = Subscription.objects.filter(device=device, event=event_type, is_active=True)

    if not subscriptions.exists():
        logger.info(f"No active subscriptions found for device {device.id}, event {event_type}")
        return 0

    message_count = 0
    for subscription in subscriptions:
        if scheduled_time:
            subscription.schedule_next_message(datetime_obj=scheduled_time)
            subscription.save()

        if subscription.interval == NotificationInterval.IMMEDIATELY.value or (
            subscription.next_scheduled and subscription.next_scheduled <= timezone.now()
        ):
            from .tasks import queue_message

            result = queue_message(subscription.id)
            if result:
                message_count += 1

    return message_count
