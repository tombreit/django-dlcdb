# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import DeviceType, InRoomRecord, LentRecord, Person, Record, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.lending.models import LendingProfile

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


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendingDetailViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

        cls.room = Room.objects.create(number="A1.23", nickname="Theke")
        cls.auto_return_room = Room.objects.create(number="RETURN", is_auto_return_room=True)
        cls.external_room = Room.objects.create(number="EXTERN", is_external=True)

        # Person without a synced contract end date (triggers a soft warning).
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com")

        # Available (InRoom) lentable device -> lend flow.
        cls.available_device = cls()._create_device(edv_id="EDV-AVAIL", sap_id="1-1")
        cls.available_device.is_lentable = True
        cls.available_device.save()
        cls.available_record = InRoomRecord.objects.create(device=cls.available_device, room=cls.room)

        # Currently lent device -> return / edit flow.
        cls.lent_device = cls()._create_device(edv_id="EDV-LENT", sap_id="2-2")
        cls.lent_device.is_lentable = True
        cls.lent_device.save()
        cls.lent_record = LentRecord.objects.create(
            device=cls.lent_device,
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _lend_payload(self, **overrides):
        payload = {
            "person": self.person.id,
            "room": self.room.id,
            "lent_start_date": "2026-06-23",
            "lent_desired_end_date": "2026-07-23",
            "lent_accessories": "",
            "lent_reason": "",
            "lent_note": "",
        }
        payload.update(overrides)
        return payload

    def test_get_lend_flow_renders(self):
        response = self.client.get(reverse("lending:detail", args=[self.available_record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EDV-AVAIL")
        self.assertContains(response, 'id="person-search-input"')
        # The search input must carry name="search" or HTMX sends no query.
        self.assertContains(response, 'name="search"')
        # "Lent from" defaults to today for a new lending.
        from django.utils import timezone

        self.assertEqual(
            response.context["form"]["lent_start_date"].value(),
            timezone.localdate(),
        )
        self.assertTrue(response.context["is_lend_flow"])

    def test_get_return_flow_renders_with_person_and_return_field(self):
        response = self.client.get(reverse("lending:detail", args=[self.lent_record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mustermann")
        self.assertContains(response, 'name="lent_end_date"')
        self.assertTrue(response.context["is_return_flow"])

    def test_lend_creates_new_lent_record(self):
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(),
        )
        self.assertRedirects(response, reverse("lending:index"))
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.LENT)
        self.assertEqual(self.available_device.active_record.person, self.person)

    def test_return_creates_auto_return_inroom_record(self):
        inroom_before = InRoomRecord.objects.filter(device=self.lent_device).count()
        response = self.client.post(
            reverse("lending:detail", args=[self.lent_record.pk]),
            self._lend_payload(lent_end_date="2026-06-23"),
        )
        self.assertRedirects(response, reverse("lending:index"))
        self.lent_device.refresh_from_db()
        self.assertEqual(self.lent_device.active_record.record_type, Record.INROOM)
        self.assertEqual(self.lent_device.active_record.room, self.auto_return_room)
        self.assertEqual(InRoomRecord.objects.filter(device=self.lent_device).count(), inroom_before + 1)

    def test_edit_lent_record_without_end_date_keeps_it_lent(self):
        response = self.client.post(
            reverse("lending:detail", args=[self.lent_record.pk]),
            self._lend_payload(lent_note="Charger included"),
        )
        self.assertRedirects(response, reverse("lending:index"))
        self.lent_device.refresh_from_db()
        self.assertEqual(self.lent_device.active_record.record_type, Record.LENT)
        self.assertEqual(self.lent_device.active_record.lent_note, "Charger included")

    def test_missing_required_person_redisplays_form(self):
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(person=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        # No new lending was created (device stays available).
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)

    @override_settings(LANGUAGE_CODE="en")
    def test_soft_warning_when_no_contract_end_date(self):
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(),
            follow=True,
        )
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("contract end date" in m.lower() for m in messages))

    @override_settings(LANGUAGE_CODE="en")
    def test_soft_warning_when_contract_ends_before_desired_return(self):
        self.person.udb_contract_planned_checkout = datetime.date(2026, 6, 30)
        self.person.save()
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(lent_desired_end_date="2026-07-23"),
            follow=True,
        )
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("contract ends before" in m.lower() for m in messages))

    def test_missing_auto_return_room_errors_and_rolls_back(self):
        self.auto_return_room.delete()
        self.client.post(
            reverse("lending:detail", args=[self.lent_record.pk]),
            self._lend_payload(lent_end_date="2026-06-23"),
            follow=True,
        )
        self.lent_device.refresh_from_db()
        # Still lent, no auto-return InRoomRecord created.
        self.assertEqual(self.lent_device.active_record.record_type, Record.LENT)
        self.assertFalse(InRoomRecord.objects.filter(device=self.lent_device).exists())

    def test_unknown_pk_returns_404(self):
        response = self.client.get(reverse("lending:detail", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("lending:detail", args=[self.available_record.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_permission_required(self):
        plain = get_user_model().objects.create_user(email="plain@example.com", password="secret", username="plain")
        self.client.force_login(plain)
        response = self.client.post(reverse("lending:detail", args=[self.available_record.pk]), self._lend_payload())
        # htmx_permission_required short-circuits with a client refresh, no save.
        self.assertEqual(response["HX-Refresh"], "true")
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendingPersonSearchTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com")
        cls.other = Person.objects.create(first_name="Erika", last_name="Beispiel", email="erika@example.com")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("lending:person_search")

    def test_empty_search_returns_no_people(self):
        response = self.client.post(self.url, {"search": ""})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Mustermann")

    def test_wildcard_returns_all(self):
        response = self.client.post(self.url, {"search": "*"})
        self.assertContains(response, "Mustermann")
        self.assertContains(response, "Beispiel")

    def test_name_search_matches(self):
        response = self.client.post(self.url, {"search": "muster"})
        self.assertContains(response, "Mustermann")
        self.assertNotContains(response, "Beispiel")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendingPrintSheetTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room = Room.objects.create(number="A1.23")
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com")

        cls.device_type = DeviceType.objects.get_or_create(name="Notebook", prefix="NTB")[0]
        cls.device = cls()._create_device(device_type=cls.device_type, edv_id="EDV-PRINT", sap_id="9-9")
        cls.device.is_lentable = True
        cls.device.save()
        cls.record = InRoomRecord.objects.create(device=cls.device, room=cls.room)

        LendingProfile.objects.create(
            device_type=cls.device_type,
            lent_sheet_template=(
                "{% load i18n %}Ausleihzettel fuer {{ record.person }} "
                "bis {{ record.lent_desired_end_date|date:'Y-m-d' }}"
            ),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("lending:print_sheet", args=[self.device.pk])

    def _payload(self, **overrides):
        payload = {
            "person": self.person.id,
            "room": self.room.id,
            "lent_start_date": "2026-06-23",
            "lent_desired_end_date": "2026-07-23",
            "lent_accessories": "",
            "lent_reason": "",
            "lent_note": "",
        }
        payload.update(overrides)
        return payload

    def test_print_renders_from_unsaved_post_without_creating_record(self):
        lent_before = LentRecord.objects.count()
        response = self.client.post(self.url, self._payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mustermann")
        self.assertContains(response, "2026-07-23")
        # Printing must not persist a lending.
        self.assertEqual(LentRecord.objects.count(), lent_before)

    def test_print_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_print_404_without_lending_profile(self):
        LendingProfile.objects.all().delete()
        response = self.client.post(self.url, self._payload())
        self.assertEqual(response.status_code, 404)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendingDeviceSearchTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room = Room.objects.create(number="A1.23")

        # Available (InRoom) lentable device -> must be searchable.
        cls.available_device = cls()._create_device(edv_id="EDV-AVAIL", sap_id="1-1")
        cls.available_device.is_lentable = True
        cls.available_device.save()
        InRoomRecord.objects.create(device=cls.available_device, room=cls.room)

        # Currently lent device -> must NOT appear (not available).
        cls.lent_device = cls()._create_device(edv_id="EDV-LENT", sap_id="2-2")
        cls.lent_device.is_lentable = True
        cls.lent_device.save()
        LentRecord.objects.create(
            device=cls.lent_device,
            person=Person.objects.create(first_name="Max", last_name="Mustermann"),
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("theme:device_search")

    def test_empty_search_returns_no_devices(self):
        response = self.client.post(self.url, {"source": "lend", "q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "EDV-AVAIL")

    def test_wildcard_returns_all_available(self):
        response = self.client.post(self.url, {"source": "lend", "q": "*"})
        self.assertContains(response, "EDV-AVAIL")
        self.assertNotContains(response, "EDV-LENT")

    def test_search_matches_edv(self):
        response = self.client.post(self.url, {"source": "lend", "q": "AVAIL"})
        self.assertContains(response, "EDV-AVAIL")

    def test_lent_device_not_searchable(self):
        response = self.client.post(self.url, {"source": "lend", "q": "LENT"})
        self.assertNotContains(response, "EDV-LENT")

    def test_device_search_uses_q_not_search(self):
        # On the quick-lend page both pickers sit in one <form>; HTMX includes a
        # stray (empty) "search" from the person picker. Device search must key
        # off "q" only, so the stray param does not blank the results.
        response = self.client.post(self.url, {"source": "lend", "q": "*", "search": ""})
        self.assertContains(response, "EDV-AVAIL")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class QuickLendViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

        cls.room = Room.objects.create(number="A1.23", nickname="Theke")
        cls.auto_return_room = Room.objects.create(number="RETURN", is_auto_return_room=True)
        cls.external_room = Room.objects.create(number="EXTERN", is_external=True)

        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com")

        cls.available_device = cls()._create_device(edv_id="EDV-AVAIL", sap_id="1-1")
        cls.available_device.is_lentable = True
        cls.available_device.save()
        cls.available_record = InRoomRecord.objects.create(device=cls.available_device, room=cls.room)

        cls.lent_device = cls()._create_device(edv_id="EDV-LENT", sap_id="2-2")
        cls.lent_device.is_lentable = True
        cls.lent_device.save()
        cls.lent_record = LentRecord.objects.create(
            device=cls.lent_device,
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("lending:quick_lend")

    def _payload(self, **overrides):
        payload = {
            "device": self.available_device.pk,
            "person": self.person.id,
            "room": self.room.id,
            "lent_start_date": "2026-06-23",
            "lent_desired_end_date": "2026-07-23",
            "lent_accessories": "",
            "lent_reason": "",
            "lent_note": "",
        }
        payload.update(overrides)
        return payload

    def test_get_renders_both_pickers(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="device-search-input"')
        self.assertContains(response, 'id="person-search-input"')
        self.assertContains(response, 'id="id_device"')
        self.assertContains(response, 'id="id_room"')

    def test_get_renders_print_button(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'id="quick-lend-print"')
        # The print endpoint is keyed on the device pk, substituted by JS.
        self.assertContains(response, "/0/print/")

    def test_device_option_exposes_lending_profile_flag(self):
        # A profile exists for the available device's type -> option flag is "1".
        LendingProfile.objects.create(device_type=self.available_device.device_type, lent_sheet_template="x")
        response = self.client.post(reverse("theme:device_search"), {"source": "lend", "q": "AVAIL"})
        self.assertContains(response, 'data-has-profile="1"')

    def test_print_sheet_works_from_quick_lend_payload(self):
        LendingProfile.objects.create(
            device_type=self.available_device.device_type,
            lent_sheet_template="{% load i18n %}Slip {{ record.person }}",
        )
        lent_before = LentRecord.objects.count()
        response = self.client.post(
            reverse("lending:print_sheet", args=[self.available_device.pk]),
            self._payload(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mustermann")
        # Printing must not persist a lending.
        self.assertEqual(LentRecord.objects.count(), lent_before)

    def test_post_creates_lent_record_and_redirects(self):
        response = self.client.post(self.url, self._payload())
        self.assertRedirects(response, reverse("lending:index"))
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.LENT)
        self.assertEqual(self.available_device.active_record.person, self.person)
        self.assertEqual(self.available_device.active_record.room, self.room)

    def test_post_rejects_non_inroom_record(self):
        lent_before = LentRecord.objects.filter(record_type=Record.LENT).count()
        response = self.client.post(self.url, self._payload(device=self.lent_device.pk))
        self.assertRedirects(response, reverse("lending:quick_lend"))
        self.assertEqual(LentRecord.objects.filter(record_type=Record.LENT).count(), lent_before)

    def test_post_missing_device_redirects(self):
        response = self.client.post(self.url, self._payload(device=""))
        self.assertRedirects(response, reverse("lending:quick_lend"))
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)

    def test_post_soft_warning_no_contract_end(self):
        response = self.client.post(self.url, self._payload(), follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("contract end date" in m.lower() for m in messages))

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_permission_required(self):
        plain = get_user_model().objects.create_user(email="plain@example.com", password="secret", username="plain")
        self.client.force_login(plain)
        response = self.client.post(self.url, self._payload())
        self.assertEqual(response["HX-Refresh"], "true")
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)
