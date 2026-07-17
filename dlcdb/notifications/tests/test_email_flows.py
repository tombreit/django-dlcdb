# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
End-to-end tests for the subscription-based notification mail flows:
subscription creation via the services API, message queueing and delivery
through the email channel.
"""

from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from dlcdb.core.models import Device, DeviceType, Person
from dlcdb.organization.models import Branding
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Message, Subscription
from dlcdb.notifications.services import create_license_subscriptions, delete_license_subscriptions
from dlcdb.notifications.tasks import queue_message, send_message


def create_license_device():
    device_type, _ = DeviceType.objects.get_or_create(name="Lizenz", prefix="lic")
    return Device.objects.create(
        device_type=device_type,
        edv_id="lic001",
        is_licence=True,
        contract_start_date=timezone.now().date() - timedelta(days=365),
        contract_expiration_date=timezone.now().date() + timedelta(days=30),
    )


class LicenseSubscriptionTests(TestCase):
    def setUp(self):
        self.subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        self.device = create_license_device()

    def test_create_license_subscriptions_creates_all_license_events(self):
        create_license_subscriptions(self.subscriber, self.device)

        events = set(Subscription.objects.values_list("event", flat=True))
        self.assertEqual(events, set(Subscription.LICENSE_EVENTS))

    def test_scheduled_times_create_point_in_time_subscriptions(self):
        expires_at = timezone.now() + timedelta(days=30)
        create_license_subscriptions(
            self.subscriber,
            self.device,
            scheduled_times={Subscription.NotificationEventChoices.CONTRACT_EXPIRES_SOON: expires_at},
        )

        subscription = Subscription.objects.get(event=Subscription.NotificationEventChoices.CONTRACT_EXPIRES_SOON)
        self.assertEqual(subscription.interval, NotificationInterval.POINT_IN_TIME.value)
        self.assertEqual(subscription.next_scheduled, expires_at)

    def test_delete_license_subscriptions_removes_all_pair_subscriptions(self):
        create_license_subscriptions(self.subscriber, self.device)

        delete_license_subscriptions(self.subscriber, self.device)

        self.assertEqual(Subscription.objects.count(), 0)


class MessageDeliveryTests(TestCase):
    def setUp(self):
        self.subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        self.device = create_license_device()

    def create_due_subscription(self, event):
        return Subscription.objects.create(
            event=event,
            subscriber=self.subscriber,
            device=self.device,
            interval=NotificationInterval.POINT_IN_TIME.value,
            next_scheduled=timezone.now() - timedelta(minutes=5),
        )

    def test_due_subscription_sends_contract_mail(self):
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.CONTRACT_EXPIRED)

        message_id = queue_message.call_local(subscription.id)
        send_message.call_local(message_id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["max@example.org"])
        self.assertTrue(email.subject.startswith(settings.EMAIL_SUBJECT_PREFIX.strip()))
        # The subject prefix must appear exactly once.
        self.assertEqual(email.subject.count(settings.EMAIL_SUBJECT_PREFIX.strip()), 1)
        self.assertIn("License", email.subject)
        self.assertIn(f"{self.device.contract_expiration_date:%Y-%m-%d}", email.body)

        message = Message.objects.get(id=message_id)
        self.assertEqual(message.status, Message.STATUS_SENT)
        self.assertIsNotNone(message.sent_at)

        subscription.refresh_from_db()
        self.assertIsNotNone(subscription.last_sent)
        # POINT_IN_TIME subscriptions fire once and are not rescheduled.
        self.assertIsNone(subscription.next_scheduled)

    def test_moved_subscription_sends_device_moved_mail(self):
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.MOVED)

        message_id = queue_message.call_local(subscription.id)
        send_message.call_local(message_id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("moved", mail.outbox[0].subject)

    def test_email_body_contains_common_footer(self):
        branding = Branding.load()
        branding.organization_name_en = "Example Institute"
        branding.organization_it_dept_email = "it@example.org"
        branding.save()
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.CONTRACT_EXPIRED)

        message_id = queue_message.call_local(subscription.id)
        send_message.call_local(message_id)

        body = mail.outbox[0].body
        self.assertIn("-- \n", body)
        self.assertIn("Example Institute", body)
        self.assertIn("it@example.org", body)
        self.assertIn("DLCDB v", body)

    def test_future_subscription_is_not_due(self):
        subscription = Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_EXPIRED,
            subscriber=self.subscriber,
            device=self.device,
            interval=NotificationInterval.POINT_IN_TIME.value,
            next_scheduled=timezone.now() + timedelta(days=10),
        )

        message_id = queue_message.call_local(subscription.id)

        self.assertIsNone(message_id)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_content_generation_works_for_every_device_event(self):
        # Regression: templates for some events were missing and raised
        # TemplateDoesNotExist. Report events are excluded: their content is
        # authored at message creation, not rendered from templates.
        device_events = [
            event for event in Subscription.NotificationEventChoices if event not in Subscription.REPORT_EVENTS
        ]
        for event in device_events:
            subscription = Subscription.objects.create(
                event=event,
                subscriber=self.subscriber,
                device=self.device,
                interval=NotificationInterval.IMMEDIATELY.value,
            )
            message = Message.objects.create(subscription=subscription)

            subject, body = message.generate_content(force=True)

            self.assertTrue(subject, f"empty subject for event {event}")
            self.assertTrue(body, f"empty body for event {event}")

    def test_subscriber_udb_email_is_used_as_fallback(self):
        self.subscriber.email = None
        self.subscriber.udb_person_email_internal_business = "max.udb@example.org"
        self.subscriber.save()
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.CONTRACT_EXPIRED)

        message_id = queue_message.call_local(subscription.id)
        send_message.call_local(message_id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["max.udb@example.org"])

    def test_subscriber_without_email_marks_message_failed(self):
        self.subscriber.email = None
        self.subscriber.save()
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.CONTRACT_EXPIRED)

        message_id = queue_message.call_local(subscription.id)
        send_message.call_local(message_id)

        self.assertEqual(len(mail.outbox), 0)
        message = Message.objects.get(id=message_id)
        self.assertEqual(message.status, Message.STATUS_FAILED)
        self.assertIn("No recipient email address", message.error_message)

    def test_no_duplicate_message_for_pending_subscription(self):
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.CONTRACT_EXPIRED)

        first_id = queue_message.call_local(subscription.id)
        subscription.refresh_from_db()
        subscription.next_scheduled = timezone.now() - timedelta(minutes=1)
        subscription.save()
        second_id = queue_message.call_local(subscription.id)

        self.assertEqual(first_id, second_id)
        self.assertEqual(Message.objects.count(), 1)

    def test_one_shot_subscription_fires_only_once(self):
        # A device edit re-arms next_scheduled for POINT_IN_TIME subscriptions
        # (_update_license_subscriptions); the sent message must keep blocking.
        subscription = self.create_due_subscription(Subscription.NotificationEventChoices.CONTRACT_EXPIRED)

        first_id = queue_message.call_local(subscription.id)
        send_message.call_local(first_id)
        subscription.refresh_from_db()
        subscription.schedule_next_message(datetime_obj=timezone.now() - timedelta(minutes=1))
        subscription.save()
        second_id = queue_message.call_local(subscription.id)

        self.assertEqual(first_id, second_id)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_recurring_subscription_queues_again_after_send(self):
        subscription = Subscription.objects.create(
            event=Subscription.NotificationEventChoices.MOVED,
            subscriber=self.subscriber,
            device=self.device,
            interval=NotificationInterval.DAILY.value,
            next_scheduled=timezone.now() - timedelta(minutes=5),
        )

        first_id = queue_message.call_local(subscription.id)
        send_message.call_local(first_id)
        subscription.refresh_from_db()
        subscription.next_scheduled = timezone.now() - timedelta(minutes=1)
        subscription.save()
        second_id = queue_message.call_local(subscription.id)

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(Message.objects.count(), 2)
