from dlcdb.reporting.models import Subscription


def manage_subscribers(device, new_subscribers, previous_subscribers):
    new_subscribers_ids = set(new_subscribers.values_list("id", flat=True))
    previous_subscribers_ids = set(previous_subscribers)

    _unchanged_subscribers = previous_subscribers_ids & new_subscribers_ids
    deleted_subscribers = previous_subscribers_ids - new_subscribers_ids
    new_subscribers = new_subscribers_ids - previous_subscribers_ids

    # Todo: set correct subscription status
    if deleted_subscribers:
        Subscription.objects.filter(
            device=device,
            subscriber__id__in=deleted_subscribers,
        ).delete()

    if new_subscribers:
        for subscriber_id in new_subscribers:
            Subscription.objects.get_or_create(
                subscriber_id=subscriber_id,
                device=device,
            )
