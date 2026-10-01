# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The sticky hint messages (core.context_processors.hints) point to the frontend
apps, not the legacy admin changelists.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import Device, Room
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
        cls()._join_default_tenant(cls.user)

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

    def test_devices_without_tenant_hint_links_to_the_tenant_admin(self):
        self._create_device(edv_id="EDV-WITH-TENANT", sap_id="1-1")

        response = self.client.get(self.dashboard_url)
        self.assertNotContains(response, "without tenant!")

        Device.objects.create(edv_id="EDV-NO-TENANT-1", sap_id="2-2")
        Device.objects.create(edv_id="EDV-NO-TENANT-2", sap_id="3-3")

        response = self.client.get(self.dashboard_url)
        self.assertContains(response, "2 devices without tenant!")
        self.assertContains(response, reverse("admin:tenants_tenant_changelist"))
        self.assertContains(response, "Assign a tenant?")

    def test_users_without_tenant_get_a_hint(self):
        hint = "None of your groups belongs to a tenant, so you see no devices."

        # The class's superuser belongs to the default test tenant: no hint.
        self.assertNotContains(self.client.get(self.dashboard_url), hint)

        viewer = get_user_model().objects.create_user(username="no-tenant", email="no-tenant@example.com")
        viewer.user_permissions.add(Permission.objects.get(codename="view_device", content_type__app_label="core"))
        self.client.force_login(viewer)
        response = self.client.get(self.dashboard_url)
        self.assertContains(response, hint)
        self.assertContains(response, reverse("tenants:index"))

        # Superusers see only the tenants of their groups, too.
        superuser = get_user_model().objects.create_superuser(
            email="root@example.com", password="secret", username="root"
        )
        self.client.force_login(superuser)
        self.assertContains(self.client.get(self.dashboard_url), hint)

    def test_no_tenant_hint_needs_the_view_device_permission(self):
        self.client.force_login(get_user_model().objects.create_user(username="nobody", email="nobody@example.com"))
        self.assertNotContains(self.client.get(self.dashboard_url), "so you see no devices")

    def test_hints_are_not_shown_to_anonymous_users(self):
        # Every hint condition holds: a device without tenant, no rooms, no
        # Branding IT dept email.
        Device.objects.create(edv_id="EDV-NO-TENANT", sap_id="2-2")
        self.client.logout()

        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "without tenant!")
        self.assertNotContains(response, "No rooms defined yet.")
        self.assertNotContains(response, "No IT department contact email configured in Branding!")

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
