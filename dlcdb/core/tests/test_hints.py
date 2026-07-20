# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The sticky hint messages (core.context_processors.hints) point to the frontend
apps, not the legacy admin changelists.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.organization.models import Branding


_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class StickyHintsTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

    def setUp(self):
        self.client.force_login(self.user)
        self.dashboard_url = reverse("dashboard:index")

    def test_single_recordless_device_links_to_move_with_the_device_preselected(self):
        device = self._create_device(edv_id="EDV-NO-RECORD", sap_id="1-1")

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "device without record!")
        self.assertContains(response, f"{reverse('assets:relocate')}?device={device.pk}")
        self.assertContains(response, "Add proper record?")

    def test_multiple_recordless_devices_link_to_the_filtered_device_index(self):
        self._create_device(edv_id="EDV-NR-1", sap_id="1-1")
        self._create_device(edv_id="EDV-NR-2", sap_id="2-2")

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "2 devices without record!")
        self.assertContains(response, f"{reverse('assets:device_index')}?state=no-record")

    def test_room_hints_link_to_the_rooms_frontend(self):
        # No rooms at all: the hint offers the frontend add form.
        response = self.client.get(self.dashboard_url)
        self.assertContains(response, "No rooms defined yet.")
        self.assertContains(response, reverse("rooms:add"))

        # Rooms exist but none is flagged external/auto-return: the hints
        # offer the frontend room list.
        Room.objects.create(number="F1.01")
        response = self.client.get(self.dashboard_url)
        self.assertContains(response, "is_external")
        self.assertContains(response, "is_auto_return_room")
        self.assertContains(response, reverse("rooms:index"))

    def test_branding_it_email_hint_nags_until_configured(self):
        # Unconfigured Branding IT dept email: the hint nags with a CTA.
        response = self.client.get(self.dashboard_url)
        self.assertContains(response, "No IT department contact email configured in Branding!")
        self.assertContains(response, reverse("admin:organization_branding_changelist"))

        # Once set, the nag disappears.
        branding = Branding.load()
        branding.organization_it_dept_email = "it-dept@example.org"
        branding.save()
        response = self.client.get(self.dashboard_url)
        self.assertNotContains(response, "No IT department contact email configured in Branding!")
