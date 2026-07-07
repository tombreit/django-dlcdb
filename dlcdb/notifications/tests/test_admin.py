# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the notifications admin: message preview with ad-hoc sending and
Subscription validation.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dlcdb.core.models import Device, DeviceType, Person
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Message, Subscription

# Use plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class MessagePreviewAdminTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.org", password="secret"
        )
        self.client.force_login(admin_user)

    def create_subscription_message(self):
        subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        device_type, _ = DeviceType.objects.get_or_create(name="Lizenz", prefix="lic")
        device = Device.objects.create(
            device_type=device_type,
            edv_id="lic001",
            is_licence=True,
            contract_expiration_date=timezone.now().date() + timedelta(days=30),
        )
        subscription = Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_EXPIRED,
            subscriber=subscriber,
            device=device,
            interval=NotificationInterval.POINT_IN_TIME.value,
            next_scheduled=timezone.now(),
        )
        return Message.objects.create(subscription=subscription)

    def test_preview_renders_subscription_message(self):
        message = self.create_subscription_message()

        response = self.client.get(reverse("admin:notifications_message_preview", args=[message.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "max@example.org")

    def test_preview_renders_standalone_message(self):
        message = Message.objects.create(recipient_email="lender@example.org", subject="Hello", body="World")

        response = self.client.get(reverse("admin:notifications_message_preview", args=[message.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "lender@example.org")

    def test_send_now_sends_pending_message(self):
        message = Message.objects.create(recipient_email="lender@example.org", subject="Hello", body="World")

        response = self.client.post(
            reverse("admin:notifications_message_preview", args=[message.pk]), {"_send_now": "1"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["lender@example.org"])
        message.refresh_from_db()
        self.assertEqual(message.status, Message.STATUS_SENT)


class SubscriptionValidationTests(TestCase):
    def setUp(self):
        self.subscriber = Person.objects.create(first_name="ITSupport", last_name="Team", email="it@example.org")

    def subscription(self, **kwargs):
        defaults = {
            "subscriber": self.subscriber,
            "event": Subscription.NotificationEventChoices.INROOM,
            "condition": Subscription.ConditionChoices.HAS_SAP_ID,
            "interval": NotificationInterval.WEEKLY.value,
        }
        defaults.update(kwargs)
        return Subscription(**defaults)

    def test_duplicate_report_subscription_is_rejected_per_subscriber(self):
        self.subscription().save()

        with self.assertRaises(ValidationError):
            self.subscription().clean()

        other = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")
        self.subscription(subscriber=other).clean()  # different subscriber is fine

    def test_duplicate_device_subscription_is_rejected_per_subscriber(self):
        device_type, _ = DeviceType.objects.get_or_create(name="Lizenz", prefix="lic")
        device = Device.objects.create(device_type=device_type, edv_id="lic002")
        kwargs = {
            "event": Subscription.NotificationEventChoices.MOVED,
            "condition": "",
            "device": device,
        }
        self.subscription(**kwargs).save()

        with self.assertRaises(ValidationError):
            self.subscription(**kwargs).clean()

    def test_overdue_condition_requires_lent_event(self):
        subscription = self.subscription(condition=Subscription.ConditionChoices.LENT_IS_OVERDUE)

        with self.assertRaises(ValidationError):
            subscription.clean()

    @override_settings(DEBUG=False)
    def test_immediate_interval_only_allowed_in_debug_mode(self):
        subscription = self.subscription(interval=NotificationInterval.IMMEDIATELY.value)

        with self.assertRaises(ValidationError):
            subscription.clean()

    def test_point_in_time_interval_is_rejected_for_report_events(self):
        subscription = self.subscription(interval=NotificationInterval.POINT_IN_TIME.value)

        with self.assertRaises(ValidationError):
            subscription.clean()

    def test_condition_is_rejected_for_device_events(self):
        subscription = self.subscription(event=Subscription.NotificationEventChoices.MOVED)

        with self.assertRaises(ValidationError):
            subscription.clean()

    def test_device_events_require_a_device(self):
        subscription = self.subscription(event=Subscription.NotificationEventChoices.MOVED, condition="")

        with self.assertRaises(ValidationError):
            subscription.clean()
