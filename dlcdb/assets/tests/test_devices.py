# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the standalone Device frontend."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.urls import reverse

from dlcdb.assets.forms import DeviceForm
from dlcdb.core.models import Device, InRoomRecord, LentRecord, Manufacturer, Person, Room
from dlcdb.core.tests.basetest import BaseTest


_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DeviceFrontendTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room = Room.objects.create(number="A1.01")
        cls.manufacturer = Manufacturer.objects.create(name="Example Computers")

        cls.inroom_device = cls()._create_device(edv_id="EDV-AVAILABLE", sap_id="1-1")
        cls.inroom_device.manufacturer = cls.manufacturer
        cls.inroom_device.series = "Notebook One"
        cls.inroom_device.is_lentable = True
        cls.inroom_device.save()
        InRoomRecord.objects.create(device=cls.inroom_device, room=cls.room)

        cls.untracked_device = cls()._create_device(edv_id="EDV-NO-RECORD", sap_id="2-2")

        cls.duplicate_one = cls()._create_device(edv_id="EDV-DUP-1", sap_id="3-3")
        cls.duplicate_one.serial_number = "duplicate-serial"
        cls.duplicate_one.save()
        cls.duplicate_two = cls()._create_device(edv_id="EDV-DUP-2", sap_id="4-4")
        cls.duplicate_two.serial_number = "duplicate-serial"
        cls.duplicate_two.save()

    def setUp(self):
        self.client.force_login(self.user)
        self.index_url = reverse("assets:device_index")

    def test_index_renders_device_table_and_mobile_state(self):
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<table")
        self.assertContains(response, "EDV-AVAILABLE")
        self.assertContains(response, "LOKALISIERT")
        self.assertContains(response, "Add device")

    def test_index_htmx_response_is_fragment_only(self):
        response = self.client.get(self.index_url, headers={"HX-Request": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="device-list"')
        self.assertNotContains(response, "<html")

    def test_search_and_state_filters(self):
        response = self.client.get(self.index_url, {"search": "Notebook One"}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-AVAILABLE")
        self.assertNotContains(response, "EDV-NO-RECORD")

        response = self.client.get(self.index_url, {"state": "no-record"}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-NO-RECORD")
        self.assertNotContains(response, "EDV-AVAILABLE")

    def test_duplicate_serial_filter_uses_the_visible_queryset(self):
        response = self.client.get(
            self.index_url,
            {"duplicate": "serial_number"},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "EDV-DUP-1")
        self.assertContains(response, "EDV-DUP-2")
        self.assertNotContains(response, "EDV-AVAILABLE")

    def test_create_device_redirects_to_its_detail_page(self):
        response = self.client.post(
            reverse("assets:device_add"),
            {"edv_id": "EDV-NEW", "sap_id": "5-5", "is_lentable": "on"},
        )

        device = Device.objects.get(edv_id="EDV-NEW")
        self.assertRedirects(response, reverse("assets:device_detail", args=[device.pk]))
        self.assertEqual(device.user, self.user)
        self.assertTrue(device.is_lentable)

    def test_non_superuser_cannot_change_loanability_while_device_is_lent(self):
        device = self._create_device(edv_id="EDV-LENT", sap_id="6-6")
        device.is_lentable = True
        device.save()
        LentRecord.objects.create(
            device=device,
            room=self.room,
            person=Person.objects.create(first_name="Max", last_name="Mustermann"),
        )
        user = get_user_model().objects.create_user(
            username="device-operator",
            email="operator@example.com",
            password="secret",
        )
        request = RequestFactory().post("/")
        request.user = user

        form = DeviceForm(
            {"edv_id": device.edv_id, "sap_id": device.sap_id},
            instance=device,
            request=request,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("is_lentable", form.errors)
