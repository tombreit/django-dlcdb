# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
End-to-end tests for the report subscription and overdue lender mail flows:
scheduled processing, ad-hoc admin triggering, recipients, spreadsheet
attachments and per-lender grouping.
"""

import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from huey.contrib import djhuey

from dlcdb.core.models import Device, DeviceType, InRoomRecord, LentRecord, Person
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Message, Subscription
from dlcdb.notifications.tasks import notify_overdue_lenders, queue_messages_for_interval, send_message
from dlcdb.reporting.models import Report

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="dlcdb-test-media-")


def create_device(edv_id, sap_id=None):
    device_type, _ = DeviceType.objects.get_or_create(name="Notebook", prefix="ntb")
    return Device.objects.create(device_type=device_type, edv_id=edv_id, sap_id=sap_id)


def create_report_subscription(**kwargs):
    subscriber = (
        kwargs.pop("subscriber", None)
        or Person.objects.get_or_create(first_name="ITSupport", last_name="Team", email="it@example.org")[0]
    )
    defaults = {
        "subscriber": subscriber,
        "event": Subscription.NotificationEventChoices.INROOM,
        "condition": Subscription.ConditionChoices.HAS_SAP_ID,
        "interval": NotificationInterval.DAILY.value,
        # A freshly saved subscription is scheduled one interval ahead;
        # backdate it so it is due for processing.
        "next_scheduled": timezone.now() - timedelta(minutes=5),
    }
    defaults.update(kwargs)
    return Subscription.objects.create(**defaults)


class ImmediateHueyMixin:
    """Execute huey tasks inline instead of enqueueing them."""

    def setUp(self):
        super().setUp()
        djhuey.HUEY.immediate = True
        self.addCleanup(lambda: setattr(djhuey.HUEY, "immediate", False))


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ScheduledReportingTests(ImmediateHueyMixin, TestCase):
    def setUp(self):
        super().setUp()
        InRoomRecord.objects.create(device=create_device(edv_id="ntb001", sap_id="4711"))

    def test_scheduled_run_creates_report_and_sends_mail(self):
        subscription = create_report_subscription()

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)
        message = Message.objects.get()
        send_message.call_local(message.id)

        report = Report.objects.get()
        self.assertIn("INROOM", report.title)
        self.assertTrue(report.spreadsheet.name.endswith(".xlsx"))

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["it@example.org"])
        self.assertIn("DLCDB Report", email.subject)
        self.assertEqual(len(email.attachments), 1)
        self.assertTrue(email.attachments[0][0].endswith(".xlsx"))

        subscription.refresh_from_db()
        self.assertIsNotNone(subscription.last_run)

    def test_every_subscriber_gets_their_own_mail(self):
        create_report_subscription()
        second_subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        create_report_subscription(subscriber=second_subscriber)

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)
        for message in Message.objects.all():
            send_message.call_local(message.id)

        self.assertEqual(len(mail.outbox), 2)
        recipients = {address for email in mail.outbox for address in email.to}
        self.assertEqual(recipients, {"it@example.org", "max@example.org"})

        # Identical subscriptions share a single report artifact.
        self.assertEqual(Report.objects.count(), 1)
        report_ids = {message.report_id for message in Message.objects.all()}
        self.assertEqual(report_ids, {Report.objects.get().id})
        for email in mail.outbox:
            self.assertEqual(len(email.attachments), 1)

    def test_different_windows_produce_separate_reports(self):
        create_report_subscription(last_run=timezone.now() - timedelta(days=3))
        second_subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        create_report_subscription(subscriber=second_subscriber)

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        self.assertEqual(Report.objects.count(), 2)
        report_ids = {message.report_id for message in Message.objects.all()}
        self.assertEqual(len(report_ids), 2)

    def test_group_converges_after_first_shared_run(self):
        subscription1 = create_report_subscription()
        second_subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        subscription2 = create_report_subscription(subscriber=second_subscriber)

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        subscription1.refresh_from_db()
        subscription2.refresh_from_db()
        self.assertIsNotNone(subscription1.last_run)
        self.assertEqual(subscription1.last_run, subscription2.last_run)

    def test_notify_no_updates_divergence_within_group(self):
        subscription1 = create_report_subscription(
            event=Subscription.NotificationEventChoices.REMOVED, condition="", notify_no_updates=True
        )
        second_subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        subscription2 = create_report_subscription(
            subscriber=second_subscriber, event=Subscription.NotificationEventChoices.REMOVED, condition=""
        )

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        self.assertEqual(Report.objects.count(), 0)
        message = Message.objects.get()
        self.assertEqual(message.subscription, subscription1)
        subscription1.refresh_from_db()
        subscription2.refresh_from_db()
        self.assertIsNotNone(subscription1.last_run)
        self.assertIsNotNone(subscription2.last_run)

    def test_second_run_within_interval_is_skipped(self):
        create_report_subscription()

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)
        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        self.assertEqual(Message.objects.count(), 1)

    def test_no_records_with_notify_no_updates_sends_no_records_mail(self):
        create_report_subscription(
            event=Subscription.NotificationEventChoices.REMOVED, condition="", notify_no_updates=True
        )

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)
        message = Message.objects.get()
        send_message.call_local(message.id)

        self.assertEqual(Report.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("No records affected", email.subject)
        self.assertEqual(email.attachments, [])

    def test_no_records_without_notify_no_updates_creates_no_message(self):
        create_report_subscription(event=Subscription.NotificationEventChoices.REMOVED, condition="")

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        self.assertEqual(Message.objects.count(), 0)

    def test_inactive_subscription_is_skipped(self):
        create_report_subscription(is_active=False)

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        self.assertEqual(Message.objects.count(), 0)

    def test_interval_mismatch_is_skipped(self):
        create_report_subscription(interval=NotificationInterval.WEEKLY.value)

        queue_messages_for_interval.call_local(NotificationInterval.DAILY)

        self.assertEqual(Message.objects.count(), 0)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AdHocReportTriggerTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.org", password="secret"
        )
        self.client.force_login(admin_user)

    def trigger(self, subscription):
        return self.client.get(reverse("admin:notifications_subscription_trigger", args=[subscription.pk]))

    def test_trigger_sends_report_mail_with_spreadsheet(self):
        InRoomRecord.objects.create(device=create_device(edv_id="ntb003", sap_id="4713"))
        subscription = create_report_subscription()

        response = self.trigger(subscription)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["it@example.org"])
        self.assertEqual(len(email.attachments), 1)

        # Ad-hoc triggering must not shift the reporting window.
        subscription.refresh_from_db()
        self.assertIsNone(subscription.last_run)

    def test_trigger_without_records_sends_no_records_mail(self):
        subscription = create_report_subscription(
            event=Subscription.NotificationEventChoices.REMOVED, condition="", notify_no_updates=True
        )

        self.trigger(subscription)

        self.assertEqual(Report.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("No records affected", mail.outbox[0].subject)

    def test_trigger_is_refused_for_device_subscriptions(self):
        subscription = create_report_subscription(
            event=Subscription.NotificationEventChoices.MOVED, condition="", device=create_device(edv_id="ntb004")
        )

        response = self.trigger(subscription)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


# The gate and redirect settings are pinned here since both are
# environment-dependent (env.template / .env).
@override_settings(NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS=True, NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS_TO_IT=False)
class OverdueLendersMailTests(ImmediateHueyMixin, TestCase):
    """
    Overdue semantics: a lending is overdue once
    lent_desired_end_date + 5 days tolerance <= today (inclusive).
    """

    def create_lent_record(self, person, edv_id, overdue_days):
        return LentRecord.objects.create(
            device=create_device(edv_id=edv_id),
            person=person,
            lent_start_date=timezone.localdate() - timedelta(days=100),
            lent_desired_end_date=timezone.localdate() - timedelta(days=overdue_days),
        )

    def setUp(self):
        super().setUp()
        self.lender1 = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        self.lender2 = Person.objects.create(first_name="Sabine", last_name="Muster", email="sabine@example.org")

    def test_one_mail_per_overdue_lender(self):
        # lender1 has two overdue devices -> exactly one mail listing both
        self.create_lent_record(self.lender1, edv_id="ntb101", overdue_days=6)
        self.create_lent_record(self.lender1, edv_id="ntb102", overdue_days=20)
        self.create_lent_record(self.lender2, edv_id="ntb103", overdue_days=6)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 2)
        recipients = {address for email in mail.outbox for address in email.to}
        self.assertEqual(recipients, {"max@example.org", "sabine@example.org"})

        lender1_email = next(email for email in mail.outbox if email.to == ["max@example.org"])
        self.assertIn("Overdue lendings: 2 device", lender1_email.subject)
        self.assertIn("ntb101", lender1_email.body)
        self.assertIn("ntb102", lender1_email.body)

    def test_lender_without_email_is_skipped(self):
        lender_without_email = Person.objects.create(first_name="No", last_name="Mail")
        self.create_lent_record(lender_without_email, edv_id="ntb110", overdue_days=10)
        self.create_lent_record(self.lender1, edv_id="ntb111", overdue_days=10)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["max@example.org"])

    def test_lender_udb_email_is_used_as_fallback(self):
        udb_lender = Person.objects.create(
            first_name="Uwe", last_name="DB", udb_person_email_internal_business="uwe@example.org"
        )
        self.create_lent_record(udb_lender, edv_id="ntb112", overdue_days=10)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["uwe@example.org"])

    def test_lending_within_tolerance_is_not_reported(self):
        self.create_lent_record(self.lender1, edv_id="ntb104", overdue_days=3)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 0)

    def test_tolerance_boundary_is_inclusive(self):
        self.create_lent_record(self.lender1, edv_id="ntb105", overdue_days=5)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 1)

    @override_settings(NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS_TO_IT=True)
    def test_overdue_mails_can_be_redirected_to_it(self):
        self.create_lent_record(self.lender1, edv_id="ntb106", overdue_days=10)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 1)
        from django.conf import settings

        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_FROM_EMAIL])

    @override_settings(NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS=False)
    def test_overdue_mails_can_be_disabled(self):
        self.create_lent_record(self.lender1, edv_id="ntb107", overdue_days=10)

        notify_overdue_lenders.call_local()

        self.assertEqual(len(mail.outbox), 0)
