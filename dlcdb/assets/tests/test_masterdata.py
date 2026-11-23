# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The device master data (views.masterdata: types, manufacturers, suppliers), and
through them what the ModelViewSet does for every model: adding from another
form's + and back, the duplicate check while typing, returning to the filtered
list. smallstuff/tests/test_things.py covers the list, the read-only page and
the permissions.
"""

from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape

from dlcdb.core.models import DeviceType, Manufacturer, Supplier
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.theme.navigation import with_next


class MasterdataFrontendTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls()._join_default_tenant(cls.user)

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

    def test_lists_count_the_devices(self):
        for namespace, expected in [
            ("assets:device_type", "Notebook"),
            ("assets:manufacturer", "Example Computers"),
            ("assets:supplier", "Example Distribution"),
        ]:
            with self.subTest(namespace=namespace):
                response = self.client.get(reverse(f"{namespace}:index"))
                self.assertContains(response, expected)
                self.assertContains(response, '<span class="badge text-bg-light border">1</span>')

    def test_master_data_have_no_delete_page(self):
        # Deleting and deactivating stay with the superusers in the admin.
        for namespace, obj in [
            ("assets:device_type", self.device_type),
            ("assets:manufacturer", self.manufacturer),
            ("assets:supplier", self.supplier),
        ]:
            with self.subTest(namespace=namespace):
                with self.assertRaises(NoReverseMatch):
                    reverse(f"{namespace}:delete", args=[obj.pk])
                response = self.client.get(reverse(f"{namespace}:edit", args=[obj.pk]))
                self.assertIsNone(response.context["delete_url"])

    def test_device_type_search_and_has_note_filter(self):
        url = reverse("assets:device_type:index")
        self.assertContains(self.client.get(url), 'placeholder="Search name, prefix..."')

        response = self.client.get(url, {"search": "NTB"}, headers={"HX-Request": "true"})
        self.assertContains(response, "Notebook")
        self.assertNotContains(response, "Monitor")

        response = self.client.get(url, {"has_note": "has_note"}, headers={"HX-Request": "true"})
        self.assertContains(response, "Notebook")
        self.assertNotContains(response, "Monitor")

    def test_create_device_type_with_icon(self):
        response = self.client.post(
            reverse("assets:device_type:add"),
            {"name": "Dockingstation", "prefix": "DOC", "icon": "bi-usb-plug"},
        )

        device_type = DeviceType.objects.get(name="Dockingstation")
        self.assertRedirects(response, reverse("assets:device_type:edit", args=[device_type.pk]))
        self.assertEqual(device_type.icon, "bi-usb-plug")

    def test_device_type_form_ships_the_icon_picker_assets(self):
        response = self.client.get(reverse("assets:device_type:add"))
        self.assertContains(response, "iconpicker.js")
        self.assertContains(response, "iconpicker.css")

    def test_the_edit_page_links_the_devices_to_the_filtered_device_list(self):
        device_index = reverse("assets:device_index")
        for namespace, obj, param in [
            ("assets:device_type", self.device_type, "device_type"),
            ("assets:manufacturer", self.manufacturer, "manufacturer"),
            ("assets:supplier", self.supplier, "supplier"),
        ]:
            with self.subTest(namespace=namespace):
                response = self.client.get(reverse(f"{namespace}:edit", args=[obj.pk]))
                self.assertEqual(response.context["usage"]["count"], 1)
                self.assertContains(response, f'href="{device_index}?{param}={obj.pk}"')

    def test_device_index_filters_by_supplier(self):
        other = self._create_device(edv_id="EDV-NO-SUPPLIER", sap_id="2-2")
        self.assertIsNone(other.supplier)

        response = self.client.get(
            reverse("assets:device_index"), {"supplier": self.supplier.pk}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "EDV-1")
        self.assertNotContains(response, "EDV-NO-SUPPLIER")

    # The device form that opened the add page, with its own way back and an
    # earlier pick in another select.
    OPENER = "/assets/devices/7/?next=/assets/devices/&supplier=3"

    def _add_url(self, url_name, next_url=OPENER, next_field="manufacturer"):
        return f"{with_next(reverse(url_name), next_url)}&next_field={next_field}"

    def test_add_returns_to_the_form_that_opened_it_with_the_new_object(self):
        response = self.client.post(self._add_url("assets:manufacturer:add"), {"name": "Dell"})

        manufacturer = Manufacturer.objects.get(name="Dell")
        self.assertRedirects(response, f"{self.OPENER}&manufacturer={manufacturer.pk}", fetch_redirect_response=False)

    def test_add_replaces_an_earlier_pick_of_the_same_select(self):
        response = self.client.post(self._add_url("assets:supplier:add", next_field="supplier"), {"name": "Acme"})

        supplier = Supplier.objects.get(name="Acme")
        self.assertRedirects(
            response, f"/assets/devices/7/?next=/assets/devices/&supplier={supplier.pk}", fetch_redirect_response=False
        )

    def test_add_page_cancels_to_the_form_that_opened_it(self):
        response = self.client.get(self._add_url("assets:device_type:add"))

        self.assertContains(response, f'href="{escape(self.OPENER)}"', count=2)  # header and action bar

    def test_add_without_a_safe_next_opens_the_new_object(self):
        response = self.client.post(
            self._add_url("assets:manufacturer:add", next_url="https://evil.example/"), {"name": "Dell"}
        )

        manufacturer = Manufacturer.objects.get(name="Dell")
        self.assertRedirects(response, reverse("assets:manufacturer:edit", args=[manufacturer.pk]))

    def test_add_with_an_odd_next_field_returns_without_the_new_object(self):
        response = self.client.post(
            self._add_url("assets:manufacturer:add", next_field="manu%20facturer"), {"name": "Dell"}
        )

        self.assertRedirects(response, self.OPENER, fetch_redirect_response=False)

    def test_add_refuses_another_spelling_of_an_existing_name(self):
        for url_name, name, message in [
            ("assets:device_type:add", "NOTE-BOOK", "Device type “Notebook” already exists."),
            # A case variant used to reach the database constraint and its
            # technical "Constraint … is violated" message.
            ("assets:manufacturer:add", "example computers", "Manufacturer “Example Computers” already exists."),
            ("assets:supplier:add", "Example Distribution GmbH", "Supplier “Example Distribution” already exists."),
        ]:
            with self.subTest(url_name=url_name):
                response = self.client.post(reverse(url_name), {"name": name, "prefix": ""})

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
                self.assertNotContains(response, "Constraint")
                self.assertContains(response, "alert-danger")

    def test_a_similar_name_does_not_stop_the_save(self):
        # "Example" starts "Example Distribution": a hint while typing, no obstacle.
        response = self.client.post(reverse("assets:supplier:add"), {"name": "Example"})

        supplier = Supplier.objects.get(name="Example")
        self.assertRedirects(response, reverse("assets:supplier:edit", args=[supplier.pk]))

    def test_a_name_of_noise_words_only_is_compared_too(self):
        Manufacturer.objects.create(name="AG")

        response = self.client.post(reverse("assets:manufacturer:add"), {"name": "ag"})

        self.assertContains(response, "Manufacturer “AG” already exists.")
        self.assertNotContains(response, "Constraint")

    def test_use_this_one_returns_to_the_form_with_the_existing_entry(self):
        response = self.client.post(self._add_url("assets:manufacturer:add"), {"name": "example computers"})

        use_url = f"{self.OPENER}&manufacturer={self.manufacturer.pk}"
        self.assertContains(response, f'href="{escape(use_url)}"')

    def test_use_this_one_opens_the_existing_entry_on_an_add_page_opened_from_the_list(self):
        response = self.client.post(reverse("assets:manufacturer:add"), {"name": "example computers"})

        self.assertContains(response, f'href="{reverse("assets:manufacturer:edit", args=[self.manufacturer.pk])}"')

    def test_typing_a_name_lists_similar_entries(self):
        url = self._add_url("assets:supplier:add", next_field="supplier")

        response = self.client.get(f"{url}&name=Example+Distr", headers={"HX-Request": "true"})

        self.assertNotContains(response, "<html")
        self.assertContains(response, "Similar existing entries")
        # "Use this one" returns to the device form with this supplier instead.
        use_url = f"/assets/devices/7/?next=/assets/devices/&supplier={self.supplier.pk}"
        self.assertContains(response, f'href="{escape(use_url)}"')

    def test_typing_lists_nothing_below_two_letters(self):
        response = self.client.get(f"{reverse('assets:supplier:add')}?name=E", headers={"HX-Request": "true"})

        # The answer to the typing, not the page, and empty.
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")
        self.assertNotContains(response, "alert")

    def test_the_name_input_asks_its_own_page_for_suggestions(self):
        url = self._add_url("assets:manufacturer:add")

        response = self.client.get(url)

        self.assertContains(response, f'hx-get="{escape(url)}"')
        self.assertContains(response, 'hx-target="#similar-names"')

    def test_create_manufacturer_requires_a_name(self):
        response = self.client.post(reverse("assets:manufacturer:add"), {"name": "", "note": "nameless"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is-invalid")
        self.assertFalse(Manufacturer.objects.filter(note="nameless").exists())

    def test_edit_supplier_returns_to_the_filtered_index(self):
        url = with_next(
            reverse("assets:supplier:edit", args=[self.supplier.pk]),
            reverse("assets:supplier:index") + "?search=Example",
        )
        response = self.client.post(
            url,
            {"name": "Example Distribution", "contact": "hotline@example.com", "note": ""},
        )

        self.assertRedirects(response, reverse("assets:supplier:index") + "?search=Example")
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.contact, "hotline@example.com")

    def test_edit_device_type_stamps_the_editor(self):
        self.client.post(
            reverse("assets:device_type:edit", args=[self.device_type.pk]),
            {"name": "Notebook", "prefix": "NTB", "icon": "", "note": "Loan pool devices, renewed"},
        )

        self.device_type.refresh_from_db()
        self.assertEqual(self.device_type.note, "Loan pool devices, renewed")
        self.assertEqual(self.device_type.user, self.user)
