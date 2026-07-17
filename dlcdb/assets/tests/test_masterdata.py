# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the device master-data frontends (types, manufacturers, suppliers)."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import DeviceType, Manufacturer, Supplier
from dlcdb.core.tests.basetest import BaseTest


_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class MasterdataFrontendTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

        cls.device_type = DeviceType.objects.create(name="Notebook", prefix="NTB", note="Loan pool devices")
        cls.other_device_type = DeviceType.objects.create(name="Monitor", prefix="MON")
        cls.manufacturer = Manufacturer.objects.create(name="Example Computers")
        cls.supplier = Supplier.objects.create(name="Example Distribution", contact="support@example.com")

        device = cls()._create_device(device_type=cls.device_type, edv_id="EDV-1", sap_id="1-1")
        device.manufacturer = cls.manufacturer
        device.supplier = cls.supplier
        device.save()

    def setUp(self):
        self.client.force_login(self.user)

    def test_indexes_render_with_device_counts(self):
        for url_name, expected in [
            ("assets:device_type_index", "Notebook"),
            ("assets:manufacturer_index", "Example Computers"),
            ("assets:supplier_index", "Example Distribution"),
        ]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected)
                self.assertContains(response, '<span class="badge text-bg-light border">1</span>')

    def test_index_htmx_responses_are_fragment_only(self):
        for url_name, list_id in [
            ("assets:device_type_index", "device-type-list"),
            ("assets:manufacturer_index", "manufacturer-list"),
            ("assets:supplier_index", "supplier-list"),
        ]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name), headers={"HX-Request": "true"})
                self.assertContains(response, f'id="{list_id}"')
                self.assertNotContains(response, "<html")

    def test_device_type_search_and_has_note_filter(self):
        url = reverse("assets:device_type_index")

        response = self.client.get(url, {"search": "NTB"}, headers={"HX-Request": "true"})
        self.assertContains(response, "Notebook")
        self.assertNotContains(response, "Monitor")

        response = self.client.get(url, {"has_note": "has_note"}, headers={"HX-Request": "true"})
        self.assertContains(response, "Notebook")
        self.assertNotContains(response, "Monitor")

    def test_create_device_type_with_icon(self):
        response = self.client.post(
            reverse("assets:device_type_add"),
            {"name": "Dockingstation", "prefix": "DOC", "icon": "bi-usb-plug"},
        )

        device_type = DeviceType.objects.get(name="Dockingstation")
        self.assertRedirects(response, reverse("assets:device_type_detail", args=[device_type.pk]))
        self.assertEqual(device_type.user, self.user)
        self.assertEqual(device_type.icon, "bi-usb-plug")

    def test_device_type_form_ships_the_icon_picker_assets(self):
        response = self.client.get(reverse("assets:device_type_add"))
        self.assertContains(response, "iconpicker.js")
        self.assertContains(response, "iconpicker.css")

    def test_detail_links_the_device_count_to_the_filtered_device_index(self):
        device_index = reverse("assets:device_index")
        for url_name, obj, param in [
            ("assets:device_type_detail", self.device_type, "device_type"),
            ("assets:manufacturer_detail", self.manufacturer, "manufacturer"),
            ("assets:supplier_detail", self.supplier, "supplier"),
        ]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=[obj.pk]))
                self.assertContains(response, f'href="{device_index}?{param}={obj.pk}"')
                self.assertContains(response, "1 device")

    def test_device_index_filters_by_supplier(self):
        other = self._create_device(edv_id="EDV-NO-SUPPLIER", sap_id="2-2")
        self.assertIsNone(other.supplier)

        response = self.client.get(
            reverse("assets:device_index"), {"supplier": self.supplier.pk}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "EDV-1")
        self.assertNotContains(response, "EDV-NO-SUPPLIER")

    def test_create_manufacturer_requires_a_name(self):
        response = self.client.post(reverse("assets:manufacturer_add"), {"name": "", "note": "nameless"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is-invalid")
        self.assertFalse(Manufacturer.objects.filter(note="nameless").exists())

    def test_edit_supplier_returns_to_the_filtered_index(self):
        url = reverse("assets:supplier_detail", args=[self.supplier.pk]) + "?next=search%3DExample"
        response = self.client.post(
            url,
            {"name": "Example Distribution", "contact": "hotline@example.com", "note": ""},
        )

        self.assertRedirects(response, reverse("assets:supplier_index") + "?search=Example")
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.contact, "hotline@example.com")

    def test_view_only_user_gets_readonly_detail_and_cannot_post(self):
        viewer = get_user_model().objects.create_user(
            username="masterdata-viewer", email="viewer@example.com", password="secret"
        )
        from django.contrib.auth.models import Permission

        viewer.user_permissions.add(
            Permission.objects.get(codename="view_manufacturer", content_type__app_label="core")
        )
        self.client.force_login(viewer)

        url = reverse("assets:manufacturer_detail", args=[self.manufacturer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<form method="post"')

        self.assertEqual(self.client.post(url, {"name": "Hacked"}).status_code, 403)

    def test_indexes_require_view_permission(self):
        nobody = get_user_model().objects.create_user(
            username="masterdata-nobody", email="nobody@example.com", password="secret"
        )
        self.client.force_login(nobody)

        for url_name in ["assets:device_type_index", "assets:manufacturer_index", "assets:supplier_index"]:
            with self.subTest(url_name=url_name):
                self.assertEqual(self.client.get(reverse(url_name)).status_code, 403)
