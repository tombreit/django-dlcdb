# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import DeviceType, InRoomRecord, LentRecord, Person, Record, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.lending.models import LendingProfile
from dlcdb.core.tests.testingutils import establish_state

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
        establish_state(
            LentRecord,
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
        establish_state(
            LentRecord,
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
        asc = self.client.get(self.url, {"ordering": "device"}, headers={"HX-Request": "true"}).content.decode()
        desc = self.client.get(self.url, {"ordering": "-device"}, headers={"HX-Request": "true"}).content.decode()
        # "EDV-AVAIL" < "EDV-LENT" alphabetically.
        self.assertLess(asc.index("EDV-AVAIL"), asc.index("EDV-LENT"))
        self.assertLess(desc.index("EDV-LENT"), desc.index("EDV-AVAIL"))

    @override_settings(LANGUAGE_CODE="en")
    def test_filterbar_renders_dropdowns_and_sort(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertContains(response, "data-filterbar")
        # State, Type, Person dropdowns plus the sort dropdown.
        self.assertEqual(content.count("data-filterbar-label"), 4)
        # The view's own default ordering is not a sort the user picked, so
        # nothing is checked until they sort.
        self.assertNotRegex(content, r'value="-modified"\s+checked')
        self.assertContains(response, 'value="-due"')

        # An explicit ordering is reflected as a checked radio.
        sorted_content = self.client.get(self.url, {"ordering": "-due"}).content.decode()
        self.assertRegex(sorted_content, r'value="-due"\s+checked')

    @override_settings(LANGUAGE_CODE="en")
    def test_filterbar_chips_in_fragment(self):
        response = self.client.get(
            self.url,
            {"state": "overdue", "person": self.person.id},
            headers={"HX-Request": "true"},
        )
        content = response.content.decode()
        # The fragment carries the chips, but not the bar itself.
        self.assertIn("State: Overdue", content)
        self.assertIn('data-filterbar-remove="state"', content)
        self.assertIn('data-filterbar-remove="person"', content)
        self.assertIn("Clear all", content)
        self.assertNotIn("<form", content)

    def test_filterbar_chip_removal_hrefs(self):
        response = self.client.get(self.url, {"state": "overdue", "person": self.person.id, "ordering": "-due"})
        bar = response.context["filterbar"]
        # state, person, and the explicit sort.
        self.assertEqual(len(bar.chips), 3)
        state_chip = next(chip for chip in bar.chips if chip.param == "state")
        self.assertNotIn("state=", state_chip.remove_href)
        self.assertIn(f"person={self.person.id}", state_chip.remove_href)
        self.assertIn("ordering=-due", state_chip.remove_href)
        # "Clear all" drops the sort along with the filters; the view re-injects
        # its default ordering.
        self.assertEqual(bar.clear_all_href, self.url)

    @override_settings(LANGUAGE_CODE="en")
    def test_custom_sort_is_a_removable_chip(self):
        response = self.client.get(self.url, {"ordering": "-due"}, headers={"HX-Request": "true"})
        content = response.content.decode()
        self.assertIn("Sort: Due", content)
        self.assertIn('data-filterbar-remove="ordering"', content)

    @override_settings(LANGUAGE_CODE="en")
    def test_default_sort_is_not_a_chip(self):
        # The view injects ordering=-modified on every request, so a pristine
        # list must still show no chips at all.
        content = self.client.get(self.url, headers={"HX-Request": "true"}).content.decode()
        self.assertNotIn('data-filterbar-remove="ordering"', content)
        self.assertNotIn("Clear all", content)

    @override_settings(LANGUAGE_CODE="en")
    def test_show_all_badge_removed(self):
        # The legacy "Show all" reset is gone; the filterbar "Clear all" is the
        # single reset now.
        response = self.client.get(self.url, {"state": "overdue"}, headers={"HX-Request": "true"})
        self.assertNotContains(response, "Show all")
        self.assertNotContains(response, "text-bg-warning")

    @override_settings(LANGUAGE_CODE="en")
    def test_search_only_query_gets_chip_and_clear_all(self):
        # A search-only query used to have no reset affordance (chips are for
        # dropdown filters); the search chip now covers it.
        response = self.client.get(self.url, {"search": "EDV-LENT"}, headers={"HX-Request": "true"})
        content = response.content.decode()
        self.assertIn("Search: EDV-LENT", content)
        self.assertIn('data-filterbar-remove="search"', content)
        self.assertIn("Clear all", content)
        # Count summary still renders.
        self.assertRegex(content, r"\d+ of \d+ device")

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

    def test_permission_required(self):
        # A logged-in user without core.view_lentrecord is denied (403), matching
        # the nav gate that hides the "Lending" entry for the same user.
        plain = get_user_model().objects.create_user(email="plain@example.com", password="secret", username="plain")
        self.client.force_login(plain)
        self.assertEqual(self.client.get(self.url).status_code, 403)

        # Granting the permission opens the view.
        plain.user_permissions.add(Permission.objects.get(content_type__app_label="core", codename="view_lentrecord"))
        self.client.force_login(plain)  # refresh the cached permission set
        self.assertEqual(self.client.get(self.url).status_code, 200)


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
        cls.lent_record = establish_state(
            LentRecord,
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

    def _return_url(self, record=None):
        """The Return action's URL: the detail route plus the return flow marker."""
        return f"{reverse('lending:detail', args=[(record or self.lent_record).pk])}?flow=return"

    def _return_payload(self, **overrides):
        # The return form is narrow on purpose: who borrowed the device, from
        # where and for how long are not part of it (see LendingReturnForm).
        payload = {
            "lent_end_date": "2026-06-23",
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
        response = self.client.get(self._return_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mustermann")
        self.assertContains(response, 'name="lent_end_date"')
        self.assertTrue(response.context["is_return_flow"])
        # The free-text fields are editable here too, and both cards start open.
        for field in ("lent_accessories", "lent_reason", "lent_note"):
            self.assertContains(response, f'name="{field}"')
        self.assertContains(response, 'class="collapse show" id="lending-details"')
        self.assertContains(response, 'class="collapse show" id="misc-fields"')
        # The read-only lending data points at the edit form for changing it.
        self.assertContains(response, f'href="{reverse("lending:detail", args=[self.lent_record.pk])}"')

    def test_edit_flow_keeps_the_misc_card_collapsed(self):
        response = self.client.get(reverse("lending:detail", args=[self.lent_record.pk]))
        self.assertContains(response, 'class="collapse" id="misc-fields"')

    def test_return_flow_prefills_todays_return_date(self):
        from django.utils import timezone

        response = self.client.get(self._return_url())
        self.assertEqual(
            response.context["form"]["lent_end_date"].value(),
            timezone.localdate(),
        )

    def test_edit_flow_has_no_return_date_field(self):
        # Opening a lending without the return marker edits it; ending it is the
        # return flow's job, so the field is not even on the form.
        response = self.client.get(reverse("lending:detail", args=[self.lent_record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_edit_flow"])
        self.assertNotIn("lent_end_date", response.context["form"].fields)
        self.assertNotContains(response, 'name="lent_end_date"')

    def test_edit_flow_offers_the_return_action(self):
        # Editing an active lending is the one flow returning follows on from, so
        # the screen links to the return flow instead of sending the user back to
        # the list.
        response = self.client.get(reverse("lending:detail", args=[self.lent_record.pk]))
        self.assertEqual(response.context["return_url"], self._return_url())
        self.assertContains(response, f'href="{self._return_url()}"')
        self.assertContains(response, 'id="lend-form-return"')

    def test_edit_flow_return_action_keeps_the_index_filters(self):
        # The index filters travel as ?next=; the return link must carry them on,
        # so saving the return lands back on the filtered list.
        index_query = "search=EDV-LENT&ordering=-modified"
        response = self.client.get(
            reverse("lending:detail", args=[self.lent_record.pk]),
            {"next": index_query},
        )
        return_url = response.context["return_url"]
        query = parse_qs(urlparse(return_url).query)
        self.assertEqual(query["flow"], ["return"])
        self.assertEqual(query["next"], [index_query])

    def test_return_and_lend_flows_offer_no_return_action(self):
        # Nothing to return on the return screen itself, on an available device,
        # or in picker mode.
        for url in (
            self._return_url(),
            reverse("lending:detail", args=[self.available_record.pk]),
            reverse("lending:lend"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIsNone(response.context["return_url"])
                self.assertNotContains(response, 'id="lend-form-return"')

    def test_lend_flow_renders_locked_device_card(self):
        # Record mode shows the device as a read-only card: no live device picker
        # and no change/remove control on the selected card.
        response = self.client.get(reverse("lending:detail", args=[self.available_record.pk]))
        self.assertContains(response, "EDV-AVAIL")
        self.assertNotContains(response, 'id="device-search-input"')
        self.assertNotContains(response, "js-picker-clear")

    def test_lend_flow_print_button_uses_device_pk(self):
        LendingProfile.objects.create(device_type=self.available_device.device_type, lent_sheet_template="x")
        response = self.client.get(reverse("lending:detail", args=[self.available_record.pk]))
        self.assertContains(response, 'id="lend-form-print"')
        # The slip endpoint is keyed on the device pk, not the record pk.
        self.assertContains(response, reverse("lending:print_sheet", args=[self.available_device.pk]))

    def test_lend_flow_without_slip_template_offers_profile_admin(self):
        # A profile row with an empty template cannot render a slip (the database
        # template loader rejects it), so offer to fix the profile instead of a
        # print button that would 404.
        LendingProfile.objects.create(device_type=self.available_device.device_type, lent_sheet_template="")
        response = self.client.get(reverse("lending:detail", args=[self.available_record.pk]))
        self.assertNotContains(response, 'id="lend-form-print"')
        self.assertContains(response, reverse("admin:lending_lendingprofile_add"))

    def test_lend_creates_new_lent_record(self):
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(),
        )
        self.assertRedirects(response, reverse("lending:index"))
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.LENT)
        self.assertEqual(self.available_device.active_record.person, self.person)

    @override_settings(LANGUAGE_CODE="en")
    def test_lend_message_links_the_device_and_the_person(self):
        # The success message names a device and a person; both are links to
        # their detail views so the message is actionable.
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(),
            follow=True,
        )
        msg = next(str(m) for m in response.context["messages"] if "lent to" in str(m))
        self.assertIn(
            f'<a href="{reverse("assets:device_detail", args=[self.available_device.pk])}">EDV-AVAIL</a>', msg
        )
        self.assertIn(f'<a href="{reverse("persons:detail", args=[self.person.pk])}">Mustermann, Max</a>', msg)
        # Rendered as markup, not escaped into the page.
        self.assertContains(response, f'href="{reverse("persons:detail", args=[self.person.pk])}">Mustermann, Max</a>')

    def test_return_creates_auto_return_inroom_record(self):
        inroom_before = InRoomRecord.objects.filter(device=self.lent_device).count()
        response = self.client.post(self._return_url(), self._return_payload())
        self.assertRedirects(response, reverse("lending:index"))
        self.lent_device.refresh_from_db()
        self.assertEqual(self.lent_device.active_record.record_type, Record.INROOM)
        self.assertEqual(self.lent_device.active_record.room, self.auto_return_room)
        self.assertEqual(InRoomRecord.objects.filter(device=self.lent_device).count(), inroom_before + 1)

    def test_return_leaves_the_lendings_own_fields_untouched(self):
        # The return form carries neither room nor the lending's dates, so they
        # must survive the return unchanged instead of being reset to empty.
        self.client.post(
            self._return_url(),
            self._return_payload(lent_note="Scratched lid", lent_accessories="Charger missing"),
        )
        self.lent_record.refresh_from_db()
        self.assertEqual(self.lent_record.lent_end_date, datetime.date(2026, 6, 23))
        # The free-text fields are editable while returning: the condition the
        # device came back in belongs to the return.
        self.assertEqual(self.lent_record.lent_note, "Scratched lid")
        self.assertEqual(self.lent_record.lent_accessories, "Charger missing")
        self.assertEqual(self.lent_record.room, self.room)
        self.assertEqual(self.lent_record.person, self.person)
        self.assertEqual(self.lent_record.lent_start_date, datetime.date(2026, 1, 1))
        self.assertEqual(self.lent_record.lent_desired_end_date, datetime.date(2099, 1, 1))

    def test_return_without_a_date_redisplays_the_form(self):
        response = self.client.post(self._return_url(), self._return_payload(lent_end_date=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("lent_end_date", response.context["form"].errors)
        self.lent_device.refresh_from_db()
        self.assertEqual(self.lent_device.active_record.record_type, Record.LENT)

    def test_edit_flow_cannot_end_a_lending(self):
        # A return date submitted to the edit form is not a field there and must
        # be ignored -- returning goes through the Return action.
        response = self.client.post(
            reverse("lending:detail", args=[self.lent_record.pk]),
            self._lend_payload(lent_end_date="2026-06-23"),
        )
        self.assertRedirects(response, reverse("lending:index"))
        self.lent_device.refresh_from_db()
        self.assertEqual(self.lent_device.active_record.record_type, Record.LENT)
        self.lent_record.refresh_from_db()
        self.assertIsNone(self.lent_record.lent_end_date)

    @override_settings(LANGUAGE_CODE="en")
    def test_return_message_names_the_borrower(self):
        # The borrower is not submitted by the return form; the message must
        # still name them (from the record).
        response = self.client.post(self._return_url(), self._return_payload(), follow=True)
        msg = next(str(m) for m in response.context["messages"] if "acknowledged" in str(m).lower())
        self.assertIn(f'<a href="{reverse("persons:detail", args=[self.person.pk])}">Mustermann, Max</a>', msg)

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

    @override_settings(LANGUAGE_CODE="en")
    def test_no_contract_warnings_on_return(self):
        # Acknowledging a return must not surface lending soft warnings: the
        # device is coming back, so contract-vs-desired-return checks are moot.
        self.person.udb_contract_planned_checkout = datetime.date(2026, 6, 30)
        self.person.save()
        # The lending's desired return (2099-01-01) runs past the contract end
        # (2026-06-30) — the condition that warns in the lend flow — but this is a
        # return (a valid, non-future return date), so no warning should appear.
        response = self.client.post(self._return_url(), self._return_payload(), follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertFalse(any("contract ends before" in m.lower() for m in messages))
        self.assertFalse(any("contract end date" in m.lower() for m in messages))
        self.assertTrue(any("acknowledged" in m.lower() for m in messages))

    def test_missing_auto_return_room_errors_and_rolls_back(self):
        self.auto_return_room.delete()
        self.client.post(self._return_url(), self._return_payload(), follow=True)
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
        # A plain navigation must get a real 403 naming the missing permission --
        # not an empty 200 body that renders as a blank page.
        plain = get_user_model().objects.create_user(email="plain@example.com", password="secret", username="plain")
        self.client.force_login(plain)
        response = self.client.post(reverse("lending:detail", args=[self.available_record.pk]), self._lend_payload())
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Can lend a device and take it back", status_code=403)
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)

    def test_permission_required_over_htmx_refreshes_the_client(self):
        # Over HTMX the guard keeps flashing a message and refreshing the page,
        # so the error is not swapped into a fragment container.
        plain = get_user_model().objects.create_user(email="plain2@example.com", password="secret", username="plain2")
        self.client.force_login(plain)
        response = self.client.post(
            reverse("lending:detail", args=[self.available_record.pk]),
            self._lend_payload(),
            headers={"HX-Request": "true"},
        )
        self.assertEqual(response["HX-Refresh"], "true")
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)

    def _plain_user_with(self, *codenames):
        user = get_user_model().objects.create_user(email="gated@example.com", password="secret", username="gated")
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(content_type__app_label="core", codename=codename))
        self.client.force_login(user)  # refresh the cached permission set
        return user

    def _post_lend(self):
        return self.client.post(reverse("lending:detail", args=[self.available_record.pk]), self._lend_payload())

    def test_the_lend_transition_permission_opens_the_view(self):
        """Lending is guarded by the permission the ``lend`` transition declares.

        Previously it was ``core.change_lentrecord``, chosen independently of the
        lifecycle, so a grant could open the button without opening the view (or
        the other way round).
        """
        self._plain_user_with("transition_can_lend_device")

        response = self._post_lend()

        self.assertNotIn("HX-Refresh", response.headers)

    def test_the_old_crud_permission_no_longer_opens_the_view(self):
        self._plain_user_with("change_lentrecord")

        response = self._post_lend()

        self.assertEqual(response.status_code, 403)
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

    def test_print_404_when_profile_has_no_slip_template(self):
        # A profile without a template is not printable: the endpoint must 404
        # rather than blow up in the database template loader.
        LendingProfile.objects.update(lent_sheet_template="")
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
        establish_state(
            LentRecord,
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
        # In picker mode both pickers sit in one <form>; HTMX includes a
        # stray (empty) "search" from the person picker. Device search must key
        # off "q" only, so the stray param does not blank the results.
        response = self.client.post(self.url, {"source": "lend", "q": "*", "search": ""})
        self.assertContains(response, "EDV-AVAIL")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendingPickerModeViewTests(BaseTest):
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
        cls.lent_record = establish_state(
            LentRecord,
            device=cls.lent_device,
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("lending:lend")

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
        self.assertContains(response, 'id="lend-form-print"')
        # The print endpoint is keyed on the device pk, substituted by JS.
        self.assertContains(response, "/0/print/")

    def test_print_sheet_works_from_picker_mode_payload(self):
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
        self.assertRedirects(response, reverse("lending:lend"))
        self.assertEqual(LentRecord.objects.filter(record_type=Record.LENT).count(), lent_before)

    def test_post_missing_device_redirects(self):
        response = self.client.post(self.url, self._payload(device=""))
        self.assertRedirects(response, reverse("lending:lend"))
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
        self.assertEqual(response.status_code, 403)
        self.available_device.refresh_from_db()
        self.assertEqual(self.available_device.active_record.record_type, Record.INROOM)
