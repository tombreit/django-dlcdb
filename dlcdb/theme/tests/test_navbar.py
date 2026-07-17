# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The "Master data" navbar dropdown renders the nav_masterdata slot, which the
frontend apps (rooms, persons, assets) and core (admin-only leftovers) fill
via their navigation.py files.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class MasterdataNavbarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

    def test_superuser_sees_the_masterdata_dropdown_with_frontend_links(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, "Master data")
        for url_name in [
            "rooms:index",
            "persons:index",
            "assets:manufacturer_index",
            "assets:supplier_index",
            "assets:device_type_index",
        ]:
            self.assertContains(response, f'href="{reverse(url_name)}"')

    def test_user_without_permissions_sees_no_masterdata_dropdown(self):
        user = get_user_model().objects.create_user(
            username="nav-nobody", email="nobody@example.com", password="secret"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:index"))

        self.assertNotContains(response, "Master data")

    def test_dropdown_shows_only_permitted_entries(self):
        user = get_user_model().objects.create_user(
            username="nav-roomer", email="roomer@example.com", password="secret"
        )
        user.user_permissions.add(Permission.objects.get(codename="view_room", content_type__app_label="core"))
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, "Master data")
        self.assertContains(response, f'href="{reverse("rooms:index")}"')
        self.assertNotContains(response, f'href="{reverse("persons:index")}"')

    def test_active_room_page_marks_the_dropdown_and_its_entry(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("rooms:index"))

        self.assertContains(response, "dropdown-toggle active")
        self.assertContains(response, f'class="dropdown-item active" href="{reverse("rooms:index")}"')
