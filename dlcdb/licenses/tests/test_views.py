# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, Room
from dlcdb.core.tests.basetest import BaseTest

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
        # The default ordering (-modified) is reflected as a checked sort radio.
        self.assertRegex(content, r'value="-modified"\s+checked')
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

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
