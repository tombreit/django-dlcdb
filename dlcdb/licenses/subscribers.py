# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from simple_history.utils import update_change_reason
from django.utils import timezone
from datetime import timedelta

from dlcdb.core.models import Person
from dlcdb.notifications.services import delete_license_subscriptions, create_license_subscriptions
from dlcdb.notifications.models import Subscription
from dlcdb.notifications.intervals import NotificationInterval


def manage_subscribers(device, subscribers):
    """
    TODO: subscriber management should be done int the Subscription model
    """
    # print(f"MANAGE_SUBSCRIBERS {device=}, class={type(device)}, {subscribers=}")

    if subscribers is None:
        return

    # Collect change reasons for django-simple-history
    change_reasons = []

    subscribers_ids = subscribers.values_list("id", flat=True)
    new_subscribers_ids = set(subscribers_ids) if subscribers_ids else set()
    previous_subscribers_ids = set(device.subscription_set.values_list("subscriber_id", flat=True))

    # Unchanged subscribers: nothing to do here
    _subscribers_unchanged = previous_subscribers_ids & new_subscribers_ids

    # Subscribers to be removed and added: something to do about it
    subscribers_removed = previous_subscribers_ids - new_subscribers_ids
    subscribers_added = new_subscribers_ids - previous_subscribers_ids

    if subscribers_removed:
        # print(f"MANAGE_SUBSCRIBERS Deleting {subscribers_removed=}")
        _subscribers_removed = []
        for subscriber_id in subscribers_removed:
            person = Person.objects.get(id=subscriber_id)
            delete_license_subscriptions(person, device)
            _subscribers_removed.append(person)

        _subscribers_removed = [person.email for person in _subscribers_removed]
        change_reasons.append(f"Removed subscribers: {', '.join(_subscribers_removed)}")

    if subscribers_added:
        # print(f"MANAGE_SUBSCRIBERS Adding {subscribers_added=}")
        _subscribers_added = []

        # Create scheduled_times dict based on license data
        scheduled_times = {
            # For a newly created subscription, immediate notification
            Subscription.NotificationEventChoices.CONTRACT_ADDED: timezone.now(),
            # For expires_soon, 30 days before expiration (adjust as needed)
            Subscription.NotificationEventChoices.CONTRACT_EXPIRES_SOON: device.contract_expiration_date
            - timedelta(days=30)
            if device.contract_expiration_date
            else None,
            # For expired, on expiration date
            Subscription.NotificationEventChoices.CONTRACT_EXPIRED: device.contract_expiration_date
            if device.contract_expiration_date
            else None,
        }

        # Remove None values
        scheduled_times = {k: v for k, v in scheduled_times.items() if v is not None}

        for subscriber_id in subscribers_added:
            person = Person.objects.get(id=subscriber_id)
            # print(f"MANAGE_SUBSCRIBERS: {device=}/{type(device)=}, {person=}, {scheduled_times=}")
            create_license_subscriptions(
                subscriber=person,
                device=device,
                interval=NotificationInterval.POINT_IN_TIME.value,  # Use POINT_IN_TIME for scheduled events
                scheduled_times=scheduled_times,
            )
            _subscribers_added.append(person)

        _subscribers_added = [person.email for person in _subscribers_added]
        change_reasons.append(f"Added subscribers: {', '.join(_subscribers_added)}")

    if change_reasons:
        # Update the last history record with the change reason
        update_change_reason(device, "; ".join(change_reasons))

    return
