# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The settings page the gear opens: the nav_settings entries of the apps'
navigation.py, under the group each names (theme.context_processors.SETTINGS_GROUPS).
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.organization import navigation as organization_navigation

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class SettingsHubTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(email="admin@example.com", password="secret")

    def test_the_gear_opens_the_settings_page(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, f'href="{reverse("settings")}"')
        self.assertNotContains(response, '<h6 class="dropdown-header">Settings</h6>')

    def test_a_superuser_sees_every_group_in_order(self):
        self.client.force_login(self.superuser)
        content = self.client.get(reverse("settings")).content.decode()

        headings = ["Organization", "Users and access", "Modules", "Integrations", "Logs"]
        positions = [content.index(f'<h2 class="h5">{heading}</h2>') for heading in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(f'href="{reverse("tenants:index")}"', content)

    def test_only_permitted_entries_are_listed(self):
        user = get_user_model().objects.create_user(username="lender", email="lender@example.com", password="secret")
        user.user_permissions.add(Permission.objects.get(codename="view_lendingconfiguration"))
        self.client.force_login(user)
        response = self.client.get(reverse("settings"))

        self.assertContains(response, f'href="{reverse("lending:configuration")}"')
        self.assertContains(response, '<h2 class="h5">Modules</h2>')
        self.assertNotContains(response, f'href="{reverse("tenants:index")}"')
        self.assertNotContains(response, '<h2 class="h5">Users and access</h2>')

    def test_admin_entries_need_the_staff_flag(self):
        user = get_user_model().objects.create_user(username="clerk", email="clerk@example.com", password="secret")
        user.user_permissions.add(
            Permission.objects.get(codename="view_customuser", content_type__app_label="accounts"),
            Permission.objects.get(codename="view_note", content_type__app_label="core"),
        )
        self.client.force_login(user)

        def admin_urls():
            response = self.client.get(reverse("settings"))
            items = response.context["nav_items_settings"] + response.context["nav_items_masterdata"]
            return sorted(item["url"] for item in items if item["admin"])

        self.assertEqual(admin_urls(), [])
        user.is_staff = True
        user.save()
        self.assertEqual(admin_urls(), ["admin:accounts_customuser_changelist", "admin:core_note_changelist"])

    def test_admin_entries_carry_a_badge(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("settings"))

        admin_entries = [item for item in response.context["nav_items_settings"] if item["admin"]]
        self.assertTrue(admin_entries)
        self.assertContains(response, 'fw-normal">Django admin</span>', count=len(admin_entries))
        self.assertContains(response, f'href="{reverse("admin:accounts_customuser_changelist")}"')

    def test_the_filter_gets_each_entrys_search_terms(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("settings"))

        terms = organization_navigation.nav_entries[0]["search_terms"]
        self.assertContains(response, f'data-search-terms="{terms}"')
        self.assertContains(response, f'src="{static("theme/js/settings.js")}"')

    def test_a_settings_page_leads_back_to_the_settings_page(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("organization:branding"))

        self.assertContains(response, f'<a href="{reverse("settings")}" class="btn btn-outline-secondary')

    def test_an_entry_without_a_known_group_is_refused(self):
        entry = {"slot": "nav_settings", "url": "journal:index", "required_permission": "journal.view_journalentry"}
        self.client.force_login(self.superuser)

        with mock.patch("dlcdb.journal.navigation.nav_entries", [entry]), self.assertRaises(ImproperlyConfigured):
            self.client.get(reverse("settings"))
