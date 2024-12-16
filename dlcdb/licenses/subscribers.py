from simple_history.utils import update_change_reason

from dlcdb.core.models import Person
from dlcdb.reporting.models import Subscription


def manage_subscribers(instance, subscribers):
    """
    TODO: subscriber management should be done int the Subscription model
    """
    print(f"MANAGE_SUBSCRIBERS {instance=}, {subscribers=}")
    if subscribers is None:
        return

    # Collect change reasons for django-simple-history
    change_reasons = []

    subscribers_ids = subscribers.values_list("id", flat=True)
    new_subscribers_ids = set(subscribers_ids) if subscribers_ids else set()
    previous_subscribers_ids = set(instance.subscription_set.values_list("subscriber_id", flat=True))

    # Unchanged subscribers, nothing to do here
    _subscribers_unchanged = previous_subscribers_ids & new_subscribers_ids
    subscribers_removed = previous_subscribers_ids - new_subscribers_ids
    subscribers_added = new_subscribers_ids - previous_subscribers_ids

    if subscribers_removed:
        print(f"MANAGE_SUBSCRIBERS Deleting {subscribers_removed=}")
        _subscribers_removed = []
        for subscriber_id in subscribers_removed:
            person = Person.objects.get(id=subscriber_id)
            Subscription.custom_objects.delete_license_subscriptions(person, instance)
            _subscribers_removed.append(person)

        _subscribers_removed = [person.email for person in _subscribers_removed]
        change_reasons.append(f"Removed subscribers: {', '.join(_subscribers_removed)}")

    if subscribers_added:
        print(f"MANAGE_SUBSCRIBERS Adding {subscribers_added=}")
        _subscribers_added = []
        for subscriber_id in subscribers_added:
            person = Person.objects.get(id=subscriber_id)
            Subscription.custom_objects.get_or_create_license_subscription(person, instance)
            _subscribers_added.append(person)

        _subscribers_added = [person.email for person in _subscribers_added]
        change_reasons.append(f"Added subscribers: {', '.join(_subscribers_added)}")

    print(f"{change_reasons=}")
    if change_reasons:
        # Update the last history record with the change reason
        update_change_reason(instance, "; ".join(change_reasons))

    return
