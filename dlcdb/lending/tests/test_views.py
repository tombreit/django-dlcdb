# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, LentRecord, Person, Room
from dlcdb.core.tests.basetest import BaseTest

# Use plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendingIndexViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

        cls.room = Room.objects.create(number="A1.23", nickname="Theke")
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann")
        # A person without any active lending — must not show up in the person filter.
        cls.other_person = Person.objects.create(first_name="Erika", last_name="Nobody")

        # An available (InRoom) lentable device.
        available_device = cls()._create_device(edv_id="EDV-AVAIL", sap_id="1-1")
        available_device.is_lentable = True
        available_device.save()
        InRoomRecord.objects.create(device=available_device, room=cls.room)

        # A currently lent device.
        lent_device = cls()._create_device(edv_id="EDV-LENT", sap_id="2-2")
        lent_device.is_lentable = True
        lent_device.save()
        LentRecord.objects.create(
            device=lent_device,
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        # An overdue lent device (desired end date in the past, not returned).
        overdue_device = cls()._create_device(edv_id="EDV-OVERDUE", sap_id="3-3")
        overdue_device.is_lentable = True
        overdue_device.save()
        LentRecord.objects.create(
            device=overdue_device,
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2020, 1, 1),
            lent_desired_end_date=datetime.date(2020, 2, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("lending:index")

    def test_full_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<table")
        self.assertContains(response, "Person / status")
        self.assertContains(response, "<html")
        self.assertContains(response, "EDV-AVAIL")
        self.assertContains(response, "EDV-LENT")

    def test_htmx_returns_fragment_only(self):
        response = self.client.get(self.url, headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="lent-list"', content)
        self.assertNotIn("<html", content)

    def test_search_filters_results(self):
        response = self.client.get(self.url, {"search": "EDV-LENT"}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-LENT")
        self.assertNotContains(response, "EDV-AVAIL")

    def test_state_filter_available(self):
        response = self.client.get(self.url, {"state": "available"}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-AVAIL")
        self.assertNotContains(response, "EDV-LENT")

    def test_person_filter(self):
        response = self.client.get(self.url, {"person": self.person.id}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-LENT")
        self.assertNotContains(response, "EDV-AVAIL")

    def test_person_filter_lists_current_borrowers_only(self):
        person_qs = self.client.get(self.url).context["filter"].form.fields["person"].queryset
        self.assertIn(self.person, person_qs)
        self.assertNotIn(self.other_person, person_qs)

    def test_ordering_by_device_is_reversible(self):
        asc = self.client.get(self.url, {"o": "device"}, headers={"HX-Request": "true"}).content.decode()
        desc = self.client.get(self.url, {"o": "-device"}, headers={"HX-Request": "true"}).content.decode()
        # "EDV-AVAIL" < "EDV-LENT" alphabetically.
        self.assertLess(asc.index("EDV-AVAIL"), asc.index("EDV-LENT"))
        self.assertLess(desc.index("EDV-LENT"), desc.index("EDV-AVAIL"))

    def test_overdue_due_date_is_red_and_bold(self):
        response = self.client.get(self.url, headers={"HX-Request": "true"})
        content = response.content.decode()
        # The overdue row's due-date cell carries the red + bold classes.
        self.assertRegex(content, r'class="text-danger fw-semibold"[^>]*>\s*2020-02-01')
        # A non-overdue lent row's due date is not styled red.
        self.assertNotRegex(content, r'class="text-danger fw-semibold"[^>]*>\s*2099-01-01')

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
