# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.messages import get_messages
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import Device, InRoomRecord, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

# Use plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LicensesIndexViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls()._join_default_tenant(cls.user)
        cls.room = Room.objects.create(number="A1.23", nickname="Theke")

        # Two active licenses with distinct human titles (via ``series``) so
        # search and ordering are observable. ``human_title`` renders as
        # "<series> (<sap_id>)" when manufacturer/supplier are empty.
        cls.license_alpha = cls._create_license(series="Alpha", sap_id="LIC-1")
        cls.license_beta = cls._create_license(series="Beta", sap_id="LIC-2")

    @classmethod
    def _create_license(cls, *, series, sap_id):
        device = cls()._create_device(sap_id=sap_id)
        device.is_licence = True
        device.series = series
        device.contract_start_date = datetime.date(2020, 1, 1)
        device.contract_expiration_date = datetime.date(2099, 1, 1)
        device.save()
        # An active InRoomRecord makes the device's LicenceRecord visible.
        InRoomRecord.objects.create(device=device, room=cls.room)
        return device

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("licenses:index")

    def test_full_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<html")
        self.assertContains(response, "<table")
        self.assertContains(response, "Alpha")
        self.assertContains(response, "Beta")

    def test_htmx_returns_fragment_only(self):
        response = self.client.get(self.url, headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="licenses-list"', content)
        self.assertNotIn("<html", content)

    def test_search_filters_results(self):
        response = self.client.get(self.url, {"search": "Alpha"}, headers={"HX-Request": "true"})
        self.assertContains(response, "Alpha")
        self.assertNotContains(response, "Beta")

    def test_ordering_by_license_is_reversible(self):
        asc = self.client.get(self.url, {"ordering": "license"}, headers={"HX-Request": "true"}).content.decode()
        desc = self.client.get(self.url, {"ordering": "-license"}, headers={"HX-Request": "true"}).content.decode()
        # "Alpha (LIC-1)" < "Beta (LIC-2)" alphabetically.
        self.assertLess(asc.index("Alpha"), asc.index("Beta"))
        self.assertLess(desc.index("Beta"), desc.index("Alpha"))

    @override_settings(LANGUAGE_CODE="en")
    def test_filterbar_and_sort_headers_render(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertContains(response, "data-filterbar")
        # The view's own default ordering is not a sort the user picked, so no
        # radio is checked until they sort.
        self.assertNotRegex(content, r'value="-modified"\s+checked')
        sorted_content = self.client.get(self.url, {"ordering": "-modified"}).content.decode()
        self.assertRegex(sorted_content, r'value="-modified"\s+checked')
        # Sortable column headers expose their ordering params.
        self.assertContains(response, "ordering=expiry")

    @override_settings(LANGUAGE_CODE="en")
    def test_filterbar_chips_in_fragment(self):
        response = self.client.get(self.url, {"search": "Alpha"}, headers={"HX-Request": "true"})
        content = response.content.decode()
        self.assertIn("Search: Alpha", content)
        self.assertIn('data-filterbar-remove="search"', content)
        self.assertIn("Clear all", content)
        # The fragment carries chips but not the bar's <form>.
        self.assertNotIn("<form", content)

    @override_settings(LANGUAGE_CODE="en")
    def test_license_state_chip_has_readable_label(self):
        # license_state is a queryset annotation, not a model field, so the
        # filter needs an explicit label; otherwise the chip renders as
        # "[invalid name]". Both fixture licenses are contract-active.
        response = self.client.get(self.url, {"license_state": "active"}, headers={"HX-Request": "true"})
        content = response.content.decode()
        self.assertIn("License state: Active", content)
        self.assertNotIn("[invalid name]", content)

    def test_anonymous_is_refused(self):
        # An unauthorized request is a 403 whatever the reason; the 403 page
        # offers anonymous visitors a log-in link.
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 403)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LicensesPermissionTests(BaseTest):
    """Reading the licence list and writing to it are separate grants.

    The module used to be open to every logged-in user, and its edit views asked
    for ``change_licencerecord`` regardless of whether they read or wrote.
    """

    @classmethod
    def setUpTestData(cls):
        cls.room = Room.objects.create(number="B2.01", nickname="Lager")

    @staticmethod
    def _make_user(*codenames):
        user = get_user_model().objects.create_user(
            username=f"licences-{'-'.join(codenames) or 'nobody'}",
            email=f"{'-'.join(codenames) or 'nobody'}@example.com",
            password="secret",
        )
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="core"))
        return user

    def test_the_view_permission_opens_the_list(self):
        self.client.force_login(self._make_user("view_licencerecord"))
        self.assertEqual(self.client.get(reverse("licenses:index")).status_code, 200)

    def test_without_it_the_list_is_refused(self):
        self.client.force_login(self._make_user())
        self.assertEqual(self.client.get(reverse("licenses:index")).status_code, 403)

    def test_reading_does_not_allow_creating(self):
        self.client.force_login(self._make_user("view_licencerecord"))
        # licenses:new is an HTMX-only form. Over HTMX a refused request comes
        # back as a client refresh so no 403 page lands in the modal; a plain
        # navigation gets the ordinary 403.
        self.assertEqual(self.client.get(reverse("licenses:new")).status_code, 403)

        response = self.client.get(reverse("licenses:new"), headers={"HX-Request": "true"})
        self.assertEqual(response.headers["HX-Refresh"], "true")

    def test_creating_needs_the_add_permission(self):
        self.client.force_login(self._make_user("add_licencerecord"))
        response = self.client.get(reverse("licenses:new"), headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 200)

    def test_the_add_and_edit_buttons_are_hidden_from_a_read_only_user(self):
        self.client.force_login(self._make_user("view_licencerecord"))
        content = self.client.get(reverse("licenses:index")).content.decode()

        self.assertNotIn(reverse("licenses:new"), content)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LicensesTenantScopingTests(BaseTest):
    """Licences are scoped to the user's tenants like devices."""

    @classmethod
    def setUpTestData(cls):
        cls.room = Room.objects.create(number="C3.01", nickname="Server")
        cls.own_tenant = Tenant.objects.create(name="Own tenant")
        cls.foreign_tenant = Tenant.objects.create(name="Foreign tenant")

        group = Group.objects.create(name="licence-managers")
        cls.own_tenant.groups.add(group)
        cls.user = get_user_model().objects.create_user(
            username="licence-manager", email="licence-manager@example.com", password="secret"
        )
        cls.user.groups.add(group)
        cls.user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["view_licencerecord", "change_licencerecord", "add_licencerecord"],
                content_type__app_label="core",
            )
        )

        cls.own = cls._create_licence(series="Own Suite", sap_id="LIC-OWN", tenant=cls.own_tenant)
        cls.foreign = cls._create_licence(series="Foreign Suite", sap_id="LIC-FOREIGN", tenant=cls.foreign_tenant)

    @classmethod
    def _create_licence(cls, *, series, sap_id, tenant):
        device = cls()._create_device(sap_id=sap_id, tenant=tenant)
        device.is_licence = True
        device.series = series
        device.save()
        InRoomRecord.objects.create(device=device, room=cls.room)
        return device

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_shows_only_own_licences(self):
        response = self.client.get(reverse("licenses:index"))
        self.assertContains(response, "Own Suite")
        self.assertNotContains(response, "Foreign Suite")

    def test_edit_and_history_of_a_foreign_licence_are_404(self):
        htmx = {"HX-Request": "true"}
        self.assertEqual(self.client.get(reverse("licenses:edit", args=[self.own.pk]), headers=htmx).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("licenses:edit", args=[self.foreign.pk]), headers=htmx).status_code, 404
        )
        self.assertEqual(self.client.get(reverse("licenses:history", args=[self.own.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("licenses:history", args=[self.foreign.pk])).status_code, 404)

    def test_edit_of_a_device_that_is_no_licence_is_404(self):
        device = self._create_device(sap_id="NO-LICENCE", tenant=self.own_tenant)
        response = self.client.get(reverse("licenses:edit", args=[device.pk]), headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 404)

    def test_new_licence_requires_one_of_the_users_tenants(self):
        url = reverse("licenses:new")
        htmx = {"HX-Request": "true"}

        missing = self.client.post(url, {"series": "New Suite"}, headers=htmx)
        self.assertIn("tenant", missing.context["form"].errors)

        foreign = self.client.post(url, {"series": "New Suite", "tenant": self.foreign_tenant.pk}, headers=htmx)
        self.assertIn("tenant", foreign.context["form"].errors)

    def test_an_unexpected_save_error_is_journaled_not_shown(self):
        Room.objects.create(number="LIC.01", is_default_license_room=True)
        with mock.patch("dlcdb.licenses.views.lifecycle.transition_locate", side_effect=RuntimeError("boom")):
            response = self.client.post(
                reverse("licenses:new"),
                {"series": "Broken Suite", "tenant": self.own_tenant.pk},
                headers={"HX-Request": "true"},
            )

        shown = " ".join(str(message) for message in get_messages(response.wsgi_request))
        self.assertNotIn("Traceback", shown)
        entry = JournalEntry.objects.get(source="licenses.views")
        self.assertEqual(entry.level, JournalEntry.Level.ERROR)
        self.assertEqual(entry.event, "exception")
        self.assertIn("boom", entry.body)
        self.assertIn("Traceback", entry.body)
        self.assertEqual(entry.user, self.user)
        # The atomic block rolled the half-created licence back.
        self.assertFalse(Device.objects.filter(series="Broken Suite").exists())
