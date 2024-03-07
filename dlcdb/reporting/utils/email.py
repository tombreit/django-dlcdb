# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from smtplib import SMTPException

from django.conf import settings
from django.core import mail
from django.contrib.sites.models import Site
from django.template.loader import get_template
from django.urls import reverse

from .mappings import get_admin_url_for_recordtype


def build_report_email(notification=None, report=None, record_collection=None):
    """
    Send a templated email to notification recipients.
    """

    domain = Site.objects.get_current().domain
    email_template = get_template("reporting/email_notification_body.txt")
    changelist_url = "https://{}{}".format(domain, reverse(get_admin_url_for_recordtype(notification.event)))

    email_context = {
        "changelist_url": changelist_url,
        "record_collection": record_collection,
        "notification": notification,
        "report": report,
    }

    if record_collection.records:
        subject = "[dlcdb] {}".format(record_collection.title_repr)
    else:
        subject = "[dlcdb] {}: No records affected".format(notification.__str__())
        email_context.update({"msg": "No records affected by this notification"})

    if settings.DEBUG:
        subject = subject.encode("ascii", "ignore")

    # Sending emails via plain django:
    email_objs = []
    email_obj = mail.EmailMessage(
        subject=subject,
        body=email_template.render(email_context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[notification.recipient],
        cc=[notification.recipient_cc] if notification.recipient_cc else [],
    )
    if hasattr(report, "spreadsheet"):
        email_obj.attach_file(report.spreadsheet.path)

    if email_obj:
        email_objs.append(email_obj)

    return email_objs


def build_overdue_lender_email(records):
    """
    Sends out emails to individual overdue lenders.
    """
    email_template_subject = get_template("reporting/email_overdue_lenders_subject.txt")
    email_template_body = get_template("reporting/email_overdue_lenders_body.txt")

    person = records[0].person

    # In a testdrive, emails could be sent to an alternative email address
    to = settings.DEFAULT_FROM_EMAIL if settings.REPORTING_NOTIFY_OVERDUE_LENDERS_TO_IT else person.email

    email_context = {
        "subject_prefix": settings.EMAIL_SUBJECT_PREFIX,
        "records": records,
        "person": person,
        "records_count": len(records),
        "contact_email": settings.DEFAULT_FROM_EMAIL,
    }
    subject = email_template_subject.render(email_context)
    body = email_template_body.render(email_context)

    email_obj = mail.EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
        # cc=[cc],
    )

    return email_obj


def send_email(email_objs):
    """
    Sending multiple emails within one smtp connection
    Ref: https://docs.djangoproject.com/en/3.2/topics/email/#sending-multiple-emails
    """

    try:
        connection = mail.get_connection(fail_silently=False)
        messages = email_objs
        connection.send_messages(messages)
    except SMTPException as e:
        print(f"Mail Sending Failed! SMTPException was: '{e}'")
