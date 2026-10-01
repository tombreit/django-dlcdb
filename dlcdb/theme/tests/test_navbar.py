# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The "Master data" navbar dropdown renders the nav_masterdata slot, which the
frontend apps (rooms, persons, assets) and core (admin-only leftovers) fill
via their navigation.py files.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.tenants.models import Tenant

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


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class MainNavPermissionTests(TestCase):
    """Every nav entry names a real permission -- there is no login-only entry.

    "Licenses" was the last one gated on nothing but a login (a literal "true"
    in its navigation.py, honoured by a special case in the nav context
    processor). Both are gone; this pins them down.
    """

    # Assert on the nav context rather than the rendered href: the dashboard's
    # licences *tile* links to the same URL and is deliberately not
    # permission-filtered, so a markup assertion would not be about the navbar.
    def test_a_user_without_permissions_sees_no_licenses_entry(self):
        user = get_user_model().objects.create_user(
            username="nav-licenceless", email="licenceless@example.com", password="secret"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:index"))

        self.assertNotIn("licenses:index", [item["url"] for item in response.context["nav_items_main"]])

    def test_the_view_permission_reveals_the_licenses_entry(self):
        user = get_user_model().objects.create_user(
            username="nav-licencer", email="licencer@example.com", password="secret"
        )
        user.user_permissions.add(Permission.objects.get(codename="view_licencerecord", content_type__app_label="core"))
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:index"))

        self.assertIn("licenses:index", [item["url"] for item in response.context["nav_items_main"]])


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class TenantBadgeNavbarTests(TestCase):
    """The user menu names the user's tenant or counts several; no tenant is a sticky hint (see test_hints)."""

    def _login(self, *tenants):
        user = get_user_model().objects.create_user(username="badge-user", email="badge@example.com", password="secret")
        for tenant in tenants:
            group = Group.objects.create(name=f"group-of-{tenant.name}")
            tenant.groups.add(group)
            user.groups.add(group)
        self.client.force_login(user)

    def test_a_single_tenant_is_named(self):
        self._login(Tenant.objects.create(name="Physics"))
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, ">Physics</span>")

    def test_several_tenants_are_counted(self):
        self._login(Tenant.objects.create(name="Physics"), Tenant.objects.create(name="Chemistry"))
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "2 tenants")
        self.assertContains(response, "Chemistry, Physics")

    def test_no_tenant_shows_no_badge(self):
        self._login()
        response = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(response, 'class="badge text-bg-secondary ms-1"')
        self.assertNotContains(response, "No tenant set!")
