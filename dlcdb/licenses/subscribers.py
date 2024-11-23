from dlcdb.reporting.models import Notification


def manage_subscribers(device, subscribers):
    # Remove all nofifications for this device
    _deleted_notifications = Notification.objects.filter(device=device).delete()
    # print(f"{_deleted_notifications=}")

    # Set new notifications for each subscriber
    if subscribers:
        for subscriber in subscribers:
            notification = Notification(
                recipient=subscriber,
                event=Notification.LICENCE_EXPIRES,
                device=device,
                time_interval=Notification.WEEKLY,
            )
            notification.save()

    return
