def get_admin_url_for_recordtype(recordtype):
    from ...core.models import Record

    url = None

    if recordtype == Record.LENT:
        url = 'admin:core_lentrecord_changelist'
    elif recordtype == Record.REMOVED:
        url = 'admin:core_removedrecord_changelist'
    else:
        url = 'admin:core_record_changelist'

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


# def get_last_run_date(interval):
#     """
#     Get start date for last epoche, according to a choosen interval. 
#     Getting beginning of day, week, month or year, according to a chosen interval.
#     """
#     from ..core.models import DeviceType
#     from .models import Notification

#     _now = timezone.localtime(timezone.now())  # datetime.now()
#     # _last_run = _now - timedelta(days=30)
#     _last_run = None

#     if interval == Notification.EVERY_MINUTE:
#         _last_run = _now - timedelta(minutes=5)  # todo: set to 1 min for production
#     elif interval == Notification.DAILY:
#         _last_run = _now - timedelta(days=1)
#         _last_run = _last_run.replace(hour=00, minute=00)
#     elif interval == Notification.WEEKLY:
#         _last_monday = _now - timedelta( (calendar.MONDAY - _now.weekday()) % 7 )
#         _last_run = _last_monday.replace(hour=00, minute=00)

#     return _last_run
