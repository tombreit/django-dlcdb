# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The ``subscriber_emails()`` annotation (dlcdb/licenses/subscribers.py): the
distinct subscriber emails of a licence, newline-separated and ordered by email.
"""

import datetime

from dlcdb.core.models import InRoomRecord, LicenceRecord, Person, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.licenses.subscribers import subscriber_emails
from dlcdb.notifications.models import Subscription


class SubscriberEmailsTests(BaseTest):
    def _create_licence_device(self):
        device = self._create_device()
        device.is_licence = True
        device.contract_start_date = datetime.date(2020, 1, 1)
        device.contract_expiration_date = datetime.date(2099, 1, 1)
        device.save()
        # An active record makes the device's LicenceRecord visible/queryable.
        room, _ = Room.objects.get_or_create(number="A1.23")
        InRoomRecord.objects.create(device=device, room=room)
        return device

    def _subscriber_emails(self, device):
        return (
            LicenceRecord.objects.annotate(subscriber_emails=subscriber_emails()).get(device=device).subscriber_emails
        )

    def test_multiple_subscribers_are_deduped_and_ordered_by_email(self):
        device = self._create_licence_device()
        ann = Person.objects.create(first_name="Ann", last_name="Aa", email="ann@example.org")
        bob = Person.objects.create(first_name="Bob", last_name="Bb", email="bob@example.org")

        # Ann is subscribed to the SAME device under TWO different events; her
        # email must still appear only once.
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_ADDED, subscriber=ann, device=device
        )
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_EXPIRED, subscriber=ann, device=device
        )
        # Bob is subscribed once.
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_ADDED, subscriber=bob, device=device
        )

        # Deduped (ann once) and ordered by email (ann < bob), newline-joined.
        self.assertEqual(self._subscriber_emails(device), "ann@example.org\nbob@example.org")

    def test_no_subscribers_returns_none(self):
        device = self._create_licence_device()
        self.assertIsNone(self._subscriber_emails(device))

    def test_subscriber_without_email_is_ignored(self):
        device = self._create_licence_device()
        emailless = Person.objects.create(first_name="No", last_name="Mail", email=None)
        with_email = Person.objects.create(first_name="Has", last_name="Mail", email="has@example.org")
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_ADDED, subscriber=emailless, device=device
        )
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_ADDED, subscriber=with_email, device=device
        )

        self.assertEqual(self._subscriber_emails(device), "has@example.org")

    def test_subscribers_are_scoped_to_the_device(self):
        # A subscription on another device must not leak into this device's list.
        device = self._create_licence_device()
        other_device = self._create_licence_device()
        here = Person.objects.create(first_name="Here", last_name="H", email="here@example.org")
        there = Person.objects.create(first_name="There", last_name="T", email="there@example.org")
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_ADDED, subscriber=here, device=device
        )
        Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_ADDED, subscriber=there, device=other_device
        )

        self.assertEqual(self._subscriber_emails(device), "here@example.org")
        self.assertEqual(self._subscriber_emails(other_device), "there@example.org")
