# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the user-facing "My subscriptions" page: listing, the report
subscription add form, delete/toggle/trigger actions and the navbar entry.
"""

import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, Person
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.notifications.forms import ReportSubscriptionForm
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Subscription

from .test_report_flows import create_report_subscription

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="dlcdb-test-media-")

# Use plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE, MEDIA_ROOT=TEST_MEDIA_ROOT)
class MySubscriptionsViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="me@example.com", password="secret")
        cls.person = Person.objects.create(first_name="Me", last_name="Myself", email="me@example.com")
        cls.other_person = Person.objects.create(first_name="Erika", last_name="Other", email="erika@example.com")
        cls.index_url = reverse("notifications:index")

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def create_license_subscription(self):
        return Subscription.objects.create(
            event=Subscription.NotificationEventChoices.CONTRACT_EXPIRED,
            subscriber=self.person,
            device=self._create_device(),
            interval=NotificationInterval.POINT_IN_TIME.value,
        )

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_index_renders_with_form_and_table(self):
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["form"])
        self.assertContains(response, "<table")
        # All fields are listed, since there is no detail/edit view.
        self.assertContains(response, "Notify without updates")
        self.assertContains(response, "Last sent")
        self.assertContains(response, "Next scheduled")
        self.assertContains(response, "You have no subscriptions yet.")

    def test_no_matching_person_shows_notice_and_no_form(self):
        stranger = get_user_model().objects.create_superuser(
            email="nobody@example.com", username="nobody", password="secret"
        )
        self.client.force_login(stranger)

        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"])
        self.assertContains(response, "No person record matches your email address")

    def test_lists_only_own_subscriptions(self):
        create_report_subscription(subscriber=self.person)
        create_report_subscription(subscriber=self.other_person, condition=Subscription.ConditionChoices.IS_NOTEBOOK)

        response = self.client.get(self.index_url)

        self.assertEqual(list(response.context["subscriptions"]), list(self.person.subscription_set.all()))

    def test_license_subscription_row_links_to_license_edit(self):
        subscription = self.create_license_subscription()

        response = self.client.get(self.index_url)

        self.assertContains(response, reverse("licenses:edit", kwargs={"license_id": subscription.device_id}))
        self.assertNotContains(response, reverse("notifications:delete", args=[subscription.pk]))
        self.assertNotContains(response, reverse("notifications:toggle", args=[subscription.pk]))

    def test_post_creates_report_subscription(self):
        response = self.client.post(
            self.index_url,
            {
                "event": Subscription.NotificationEventChoices.INROOM,
                "condition": Subscription.ConditionChoices.HAS_SAP_ID,
                "interval": NotificationInterval.WEEKLY.value,
            },
        )

        self.assertRedirects(response, self.index_url)
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.subscriber, self.person)
        self.assertIsNotNone(subscription.next_scheduled)

    def test_duplicate_subscription_shows_non_field_error(self):
        data = {
            "event": Subscription.NotificationEventChoices.INROOM,
            "condition": Subscription.ConditionChoices.HAS_SAP_ID,
            "interval": NotificationInterval.WEEKLY.value,
        }
        self.client.post(self.index_url, data)

        response = self.client.post(self.index_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "You already have a subscription for this report.",
            response.context["form"].non_field_errors(),
        )
        self.assertEqual(Subscription.objects.count(), 1)

    def test_interval_choices_exclude_point_in_time_and_debug_only(self):
        response = self.client.get(self.index_url)
        interval_values = {value for value, _ in response.context["form"].fields["interval"].choices}
        self.assertNotIn(NotificationInterval.POINT_IN_TIME.value, interval_values)
        self.assertNotIn(NotificationInterval.IMMEDIATELY.value, interval_values)
        self.assertNotIn(NotificationInterval.HOURLY.value, interval_values)

        # DEBUG=True breaks the test client (debug toolbar URLs are not
        # registered in the test URLconf), so check the form directly.
        with override_settings(DEBUG=True):
            form = ReportSubscriptionForm(instance=Subscription(subscriber=self.person))
            interval_values = {value for value, _ in form.fields["interval"].choices}
            self.assertIn(NotificationInterval.IMMEDIATELY.value, interval_values)
            self.assertIn(NotificationInterval.HOURLY.value, interval_values)
            self.assertNotIn(NotificationInterval.POINT_IN_TIME.value, interval_values)

    def test_event_choices_limited_to_report_events(self):
        response = self.client.get(self.index_url)
        event_values = {value for value, _ in response.context["form"].fields["event"].choices if value}
        self.assertEqual(event_values, {event.value for event in Subscription.REPORT_EVENTS})

    def test_toggle_flips_is_active(self):
        subscription = create_report_subscription(subscriber=self.person)

        response = self.client.post(reverse("notifications:toggle", args=[subscription.pk]))
        self.assertRedirects(response, self.index_url)
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_active)

        self.client.post(reverse("notifications:toggle", args=[subscription.pk]))
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_active)

    def test_trigger_sends_report_mail_and_keeps_window(self):
        device = self._create_device(edv_id="ntb200", sap_id="4720")
        InRoomRecord.objects.create(device=device)
        subscription = create_report_subscription(subscriber=self.person)

        response = self.client.post(reverse("notifications:trigger", args=[subscription.pk]))

        self.assertRedirects(response, self.index_url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["me@example.com"])
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        # Ad-hoc triggering must not shift the reporting window.
        subscription.refresh_from_db()
        self.assertIsNone(subscription.last_run)

    def test_trigger_without_records_sends_no_mail(self):
        subscription = create_report_subscription(
            subscriber=self.person, event=Subscription.NotificationEventChoices.REMOVED, condition=""
        )

        response = self.client.post(reverse("notifications:trigger", args=[subscription.pk]), follow=True)

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "No report sent.")

    def test_toggle_delete_and_trigger_require_post(self):
        subscription = create_report_subscription(subscriber=self.person)

        self.assertEqual(self.client.get(reverse("notifications:toggle", args=[subscription.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("notifications:delete", args=[subscription.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("notifications:trigger", args=[subscription.pk])).status_code, 405)

    def test_delete_removes_subscription(self):
        subscription = create_report_subscription(subscriber=self.person)

        response = self.client.post(reverse("notifications:delete", args=[subscription.pk]))

        self.assertRedirects(response, self.index_url)
        self.assertFalse(Subscription.objects.filter(pk=subscription.pk).exists())

    def test_cannot_touch_foreign_subscription(self):
        subscription = create_report_subscription(subscriber=self.other_person)

        self.assertEqual(self.client.post(reverse("notifications:delete", args=[subscription.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("notifications:toggle", args=[subscription.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("notifications:trigger", args=[subscription.pk])).status_code, 404)
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_active)
        self.assertEqual(len(mail.outbox), 0)

    def test_cannot_delete_license_subscription_via_page(self):
        subscription = self.create_license_subscription()

        response = self.client.post(reverse("notifications:delete", args=[subscription.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Subscription.objects.filter(pk=subscription.pk).exists())

    def test_navbar_shows_my_subscriptions_link(self):
        response = self.client.get(self.index_url)
        self.assertContains(response, "My subscriptions")
        self.assertContains(response, self.index_url)
