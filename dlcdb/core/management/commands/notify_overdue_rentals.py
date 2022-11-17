import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.urls import reverse
from django.template.loader import get_template
# from django.utils import timezone
from django.contrib.sites.models import Site

from dlcdb.core.models import Record


class Command(BaseCommand):
    """
    Workflow:

    - cron calls this management command
    - search for all lented devices which are overdue
    - collect some stats for all devices
    - send an email for each overdue device to it-support

    Hints:

    - lent_end_date (DateField): device was returned on this date

    ```
    # /etc/cron.d/dlcdb:
    * * * * * root /path/to/venv/bin/python3 /path/to/manage.py notify_overdue_rentals
    ```
    """

    help = 'Send email about all overdue lented devices. Triggerd via os cron.'

    def handle(self, *args, **kwargs):
        # time = timezone.now().strftime('%X')
        # self.stdout.write("It's now %s" % time)

        receipient_list = [settings.IT_NOTIFICATION_EMAIL]
        from_email = settings.SERVER_EMAIL
        changelist_url = reverse('admin:core_lentrecord_changelist')
        email_template = get_template('email/notify_overdue_device.html')
        domain = Site.objects.get_current().domain
        today = datetime.date.today()

        overdue_records = Record.objects.filter(
            Q(is_active=True),
            Q(lent_desired_end_date__lte=today) & Q(lent_end_date=None)
        )
        overdue_records_count = overdue_records.count()

        for record in overdue_records:

            email_context = {
                'device': record.device,
                'lent_url': 'https://{domain}{path}'.format(
                    domain=domain,
                    path=reverse('admin:core_lentrecord_change', args=(record.device.id,)),
                ),
                'due_date': record.lent_desired_end_date,
                'changelist_url': 'https://{domain}{path}'.format(
                    domain=domain,
                    path=changelist_url,
                ),
                'overdue_records_count': overdue_records_count,
                'lender_name': record.person,
                'lender_email': record.person.email,
                'lender_url': 'https://{domain}{path}'.format(
                    domain=domain,
                    path=reverse('admin:core_person_change', args=(record.person.id,)),
                ),
            }

            # Only send notification mail if overdue_trigger_date is in the past.
            # Build overdue warning trigger date:
            overdue_trigger_date = record.lent_desired_end_date + datetime.timedelta(days=settings.LENT_OVERDUE_TOLERANCE_DAYS)

            if overdue_trigger_date < today:

                subject = 'DLCDB: Device {device} überfällig seit {due_date}'.format(
                    device=email_context.get('device'),
                    due_date=email_context.get('due_date'),
                )
                message = email_template.render(email_context)

                send_mail(
                    subject,
                    message,
                    from_email,
                    receipient_list,
                )

        # self.stdout.write("[notify due email sent]")
