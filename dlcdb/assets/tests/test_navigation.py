# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The "Devices" and "Move" navbar entries share the assets: app namespace (see
AssetsConfig.nav_entries), which used to make both entries active together
regardless of which page was open (core.context_processors.nav matched on
namespace only). Guards the active_url_names disambiguation added to fix that.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.tests.basetest import BaseTest

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DeviceMoveNavActiveStateTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

    def setUp(self):
        self.client.force_login(self.user)

    def test_devices_page_activates_only_the_devices_nav_entry(self):
        response = self.client.get(reverse("assets:device_index"))
        self.assertContains(response, f'class="nav-link active" href="{reverse("assets:device_index")}"')
        self.assertNotContains(response, f'class="nav-link active" href="{reverse("assets:relocate")}"')

    def test_relocate_page_activates_only_the_move_nav_entry(self):
        response = self.client.get(reverse("assets:relocate"))
        self.assertContains(response, f'class="nav-link active" href="{reverse("assets:relocate")}"')
        self.assertNotContains(response, f'class="nav-link active" href="{reverse("assets:device_index")}"')
