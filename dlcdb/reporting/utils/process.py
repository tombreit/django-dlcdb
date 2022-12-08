import uuid 
from collections import namedtuple
from datetime import timedelta

from django.conf import settings
from django.db.models import Q, DateField, ExpressionWrapper, F
from django.utils import timezone
from django.utils.text import slugify
from django.core.files import File
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

from ...core.models import Record
from ..settings import LENT_OVERDUE_TOLERANCE_DAYS

from .mappings import get_days_for_interval
from .representations import get_records_as_spreadsheet, get_records_as_text
from .email import build_overdue_lender_email, send_email


def get_affected_records(notification, now):
    """
    Get all items/devices which are relevant for a new report. 
    Constraints:
        * condition must match (eg. has_sap_id)
        * do not report records which were reported in an earlier report: 
          record.created_at must be greater than current time minus interval
    """

    from ...core.models import Record
    from ..models import Notification

    ReportRecords = namedtuple('ReportRecords', [
        'records',
        'text_repr',
        'file_repr',
        'title_repr',
        'created_at',
        'last_run',
    ])

    records = text_repr = file_repr = title_repr = None
    condition = notification.condition

    if notification.last_run:
        _last_run = notification.last_run
    else:
        _days = get_days_for_interval(notification.time_interval)
        # print("_days: ", _days)
        _last_run = now - timedelta(days=_days)

    # print(f"_last_run: {_last_run}")
    # print(f"now:       {now}")

    since_last_run_filter = Q(
        created_at__gte=_last_run,
        created_at__lte=now,
    )

    _records = (
        Record
        .objects
        .active_records()
        .filter(
            record_type=notification.event,
        )
    )

    if condition == Notification.HAS_SAP_ID:
        records = (
            _records
            .filter(since_last_run_filter)
            .exclude(device__sap_id__isnull=True)
            .exclude(device__sap_id__exact='')
        )
    elif condition == Notification.IS_PC:
        records = (
            _records
            .filter(since_last_run_filter)
            .filter(device__device_type__prefix='pc')
        )
    elif condition == Notification.IS_NOTEBOOK:
        records = (
            _records
            .filter(since_last_run_filter)
            .filter(device__device_type__prefix='ntb')
        )
    elif condition == Notification.IS_PC_OR_NOTEBOOK:
        records = (
            _records
            .filter(since_last_run_filter)
            .filter(Q(device__device_type__prefix='pc') | Q(device__device_type__prefix='ntb'))
        )
    elif condition == Notification.IS_NEW_PC_OR_NOTEBOOK:
        records = (
            _records
            .filter(since_last_run_filter)
            .filter(Q(device__device_type__prefix='pc') | Q(device__device_type__prefix='ntb'))
            .exclude(device__edv_id__exact='')
            .exclude(device__serial_number__exact='')
            .exclude(device__mac_address__exact='')
        )
    elif condition == Notification.LENT_IS_OVERDUE:
        records = (
            _records
            .filter(
                ~Q(lent_desired_end_date__isnull=True) | Q(lent_end_date__isnull=True)
            )
            .annotate(
                lent_desired_end_date_with_tolerance=ExpressionWrapper(
                    F('lent_desired_end_date') + timedelta(days=LENT_OVERDUE_TOLERANCE_DAYS), output_field=DateField()
                )
            )
            .filter(
                lent_desired_end_date_with_tolerance__lte=now,
            )
        )

    if records: 
        # Build a stringified title.
        title_repr = 'DLCDB Report: from {from_date} to {to_date} for {event} ({count})'.format(
            from_date=_last_run.date(),
            to_date=now.date(),
            event=notification.event,
            count=records.count(),
        )

        # title for a spreadsheet should be no more than 31 characters
        title_repr_spreadsheet = '{event}_{from_date:%Y%m%d}-{to_date:%Y%m%d}'.format(
            from_date=_last_run.date(),
            to_date=now.date(),
            event=notification.event,
            # count=records.count(),
        )

        # Build a string representation for e.g. email body
        text_repr = get_records_as_text(records=records, title=title_repr, event=notification.event)

        # Build a spreadsheet file representation of affected records.
        file_repr = get_records_as_spreadsheet(records=records, title=title_repr_spreadsheet, event=notification.event)

    return ReportRecords(
        records=records,
        text_repr=text_repr,
        file_repr=file_repr,
        title_repr=title_repr,
        last_run=_last_run,
        created_at=now,
    )


def create_report_if_needed(notification_pk, caller='huey'):
    """
    Check if we want to create a report for this notification.
    """
    from ..models import Report, Notification

    notification = Notification.objects.get(pk=notification_pk)

    if not notification.active:
        return

    Result = namedtuple('Result', [
        'record_collection',
        'report',
    ])

    _now = timezone.localtime(timezone.now())
    report = None
    record_collection = get_affected_records(notification, _now)

    if record_collection.records:
        filename = '{}_{}.xlsx'.format(slugify(record_collection.title_repr), uuid.uuid1())
        report = Report(
            notification=notification,
            body=record_collection.text_repr,
            title=record_collection.title_repr,
            spreadsheet=File(record_collection.file_repr, name=filename),
        )
        report.save()

    if caller == 'huey':
        notification.last_run = _now

        User = get_user_model()
        huey_user, _created = User.objects.get_or_create(
            username='huey',
            is_active=False,
        )

        LogEntry.objects.log_action(
            user_id=huey_user.pk,
            content_type_id=ContentType.objects.get_for_model(notification).pk,
            object_repr=str(notification),
            object_id=notification.id,
            change_message=f'Changed "last_run" by huey: {notification.last_run:%Y-%m-%d_%H-%M-%S} -> {_now:%Y-%m-%d_%H-%M-%S} ',
            action_flag=CHANGE,
        )

        notification.save()

    return Result(record_collection, report)


def create_overdue_lenders_emails(*, caller=None):
    from ..models import Notification

    # now only needed for a valid LenderNotification class
    _now = timezone.localtime(timezone.now())

    # Creating a custom notification class, as this is not implemented
    # via models and/or admins
    LenderNotification = namedtuple(
        'LenderNotification', 
        [
            'active',
            'recipient',
            'recipient_cc',
            'event',
            'condition',
            'last_run',
        ]
    )

    # ...and instanciate this class
    lender_notification = LenderNotification(
        active=settings.REPORTING_NOTIFY_OVERDUE_LENDERS,
        recipient='',
        recipient_cc=settings.DEFAULT_FROM_EMAIL,
        event=Record.LENT,
        condition=Notification.LENT_IS_OVERDUE,
        last_run=_now,
    )

    # get overdue records
    lent_overdue_record_collection = get_affected_records(lender_notification, _now)

    # group overdue records for lender/person: get pks for persons with overdue lendings
    lenders_pks = lent_overdue_record_collection.records.values_list('person__pk', flat=True)

    overdue_emails = []
    for lender_pk in set(lenders_pks):
        records_for_person = []
        for record in lent_overdue_record_collection.records.filter(person__pk=lender_pk):
            # print("user: {} for record: {} for person: {} for device: {} - {}".format(lender_pk, record, record.person, record.device, record.lent_desired_end_date))
            records_for_person.append(record)

        overdue_email = build_overdue_lender_email(records_for_person)
        overdue_emails.append(overdue_email)

    if overdue_emails:
        send_email(overdue_emails)
