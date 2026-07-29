# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import (
    Device,
    DeviceType,
    InRoomRecord,
    LentRecord,
    LostRecord,
    OrderedRecord,
    Person,
    Record,
    RemovedRecord,
    Room,
)
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.tenants.models import Tenant

# Plain static storage so tests do not require a built staticfiles manifest
# (mirrors dlcdb.lending.tests.test_views).
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


# Pin English so the UI-string assertions below are deterministic whether or not
# the German message catalog happens to be compiled (LANGUAGE_CODE is de-de).
# The record-type labels are translatable, so they resolve to the English
# msgid here.
@override_settings(STORAGES=_PLAIN_STATIC_STORAGE, LANGUAGE_CODE="en-us")
class RelocateViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room_a = Room.objects.create(number="A1.01", nickname="Office")
        cls.room_b = Room.objects.create(number="B2.02", nickname="Lab")

        cls.device = cls()._create_device(edv_id="EDV-MOVE", sap_id="1-1")
        InRoomRecord.objects.create(device=cls.device, room=cls.room_a)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("assets:relocate")

    # --- page -------------------------------------------------------------

    def test_full_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<html")
        self.assertContains(response, "Move devices")
        # Both pickers are present.
        self.assertContains(response, 'id="device-picker"')
        self.assertContains(response, 'id="room-picker"')
        # Rendered as the two-step stepper.
        self.assertContains(response, "step-badge")
        self.assertContains(response, 'id="step-device"')
        self.assertContains(response, 'id="step-room"')
        # Live selected-device count badge in the Devices header.
        self.assertContains(response, 'id="device-count"')

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    # --- search endpoints -------------------------------------------------

    def test_device_search_matches(self):
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-MOVE"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "EDV-MOVE")

    def test_device_search_empty_query_returns_nothing(self):
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": ""}, headers={"HX-Request": "true"}
        )
        self.assertNotContains(response, "EDV-MOVE")

    def test_device_search_excludes_already_selected(self):
        # The picker sends already-selected cards' hidden ``devices`` inputs along
        # with each search (hx-include); those devices must drop out of results.
        response = self.client.post(
            reverse("theme:device_search"),
            {"source": "move", "q_device": "*", "devices": [self.device.pk]},
            headers={"HX-Request": "true"},
        )
        self.assertNotContains(response, "EDV-MOVE")

    def test_room_search_matches(self):
        response = self.client.post(reverse("assets:room_search"), {"q_room": "B2.02"}, headers={"HX-Request": "true"})
        self.assertContains(response, "B2.02")
        self.assertNotContains(response, "A1.01")

    def test_search_requires_post(self):
        self.assertEqual(self.client.get(reverse("theme:device_search")).status_code, 405)

    # --- relocate logic ---------------------------------------------------

    def test_move_inroom_device_creates_new_record(self):
        before = InRoomRecord.objects.filter(device=self.device).count()
        response = self.client.post(self.url, {"devices": [self.device.pk], "new_room": self.room_b.pk})
        self.assertRedirects(response, self.url)

        self.device.refresh_from_db()
        self.assertEqual(self.device.active_record.room, self.room_b)
        self.assertEqual(self.device.active_record.record_type, Record.INROOM)
        self.assertEqual(InRoomRecord.objects.filter(device=self.device).count(), before + 1)

    def test_move_message_links_the_device_and_the_room(self):
        # The result message is a jumping-off point: both named objects link to
        # their detail views.
        response = self.client.post(self.url, {"devices": [self.device.pk], "new_room": self.room_b.pk}, follow=True)
        move_msgs = [str(m) for m in response.context["messages"] if m.level == messages.SUCCESS]
        self.assertEqual(len(move_msgs), 1)
        self.assertIn(f'<a href="{reverse("assets:device_detail", args=[self.device.pk])}">EDV-MOVE</a>', move_msgs[0])
        self.assertIn(f'<a href="{reverse("rooms:detail", args=[self.room_b.pk])}">B2.02 (Lab)</a>', move_msgs[0])
        # Rendered as markup, not as escaped text.
        self.assertContains(response, f'href="{reverse("assets:device_detail", args=[self.device.pk])}">EDV-MOVE</a>')

    def test_prefill_preselects_device_without_record(self):
        # The device detail "Set state" action links here as ?device=<pk> also
        # for a device that has no record yet (INROOM is a valid initial state).
        recordless = self._create_device(edv_id="EDV-NO-RECORD", sap_id="7-7")

        response = self.client.get(f"{self.url}?device={recordless.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_devices"], [recordless])
        self.assertContains(response, "EDV-NO-RECORD")

    def test_move_device_without_record_creates_first_inroom_record(self):
        recordless = self._create_device(edv_id="EDV-NO-RECORD", sap_id="7-7")

        response = self.client.post(self.url, {"devices": [recordless.pk], "new_room": self.room_b.pk})
        self.assertRedirects(response, self.url)

        recordless.refresh_from_db()
        self.assertEqual(recordless.active_record.record_type, Record.INROOM)
        self.assertEqual(recordless.active_record.room, self.room_b)

    def test_move_multiple_devices_to_one_room(self):
        # The multi-select picker submits several device pks; each is relocated
        # to the single chosen room and gets its own result message.
        other = self._create_device(edv_id="EDV-MOVE-2", sap_id="1-2")
        InRoomRecord.objects.create(device=other, room=self.room_a)

        response = self.client.post(
            self.url,
            {"devices": [self.device.pk, other.pk], "new_room": self.room_b.pk},
            follow=True,
        )
        self.assertRedirects(response, self.url)

        for device in (self.device, other):
            device.refresh_from_db()
            self.assertEqual(device.active_record.room, self.room_b)
            self.assertEqual(device.active_record.record_type, Record.INROOM)

        # One success message per moved device (the page also surfaces unrelated
        # environment-config warnings, so filter to the relocation results).
        move_msgs = [m for m in response.context["messages"] if m.level == messages.SUCCESS]
        self.assertEqual(len(move_msgs), 2)

    def test_failed_post_keeps_all_selected_device_cards(self):
        # No room -> re-render; both picked devices must come back as cards.
        other = self._create_device(edv_id="EDV-MOVE-2", sap_id="1-2")
        InRoomRecord.objects.create(device=other, room=self.room_a)

        response = self.client.post(self.url, {"devices": [self.device.pk, other.pk], "new_room": ""})
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context["selected_devices"], [self.device, other])
        self.assertContains(response, "EDV-MOVE")
        self.assertContains(response, "EDV-MOVE-2")

    def test_move_to_same_room_is_noop(self):
        before = InRoomRecord.objects.filter(device=self.device).count()
        response = self.client.post(self.url, {"devices": [self.device.pk], "new_room": self.room_a.pk})
        self.assertRedirects(response, self.url)

        self.assertEqual(InRoomRecord.objects.filter(device=self.device).count(), before)
        self.device.refresh_from_db()
        self.assertEqual(self.device.active_record.room, self.room_a)

    def _create_lent_device(self, edv_id, sap_id, room):
        person = Person.objects.create(first_name="Max", last_name="Mustermann")
        device = self._create_device(edv_id=edv_id, sap_id=sap_id)
        establish_state(
            LentRecord,
            device=device,
            person=person,
            room=room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )
        return device

    def test_move_lent_device_updates_room_in_place_and_warns(self):
        lent_device = self._create_lent_device("EDV-LENT", "2-2", self.room_a)
        before = lent_device.record_set.count()

        response = self.client.post(self.url, {"devices": [lent_device.pk], "new_room": self.room_b.pk}, follow=True)
        self.assertEqual(response.status_code, 200)

        lent_device.refresh_from_db()
        # The LENT record's room is updated in place; no new record is created.
        self.assertEqual(lent_device.active_record.record_type, Record.LENT)
        self.assertEqual(lent_device.active_record.room, self.room_b)
        self.assertEqual(lent_device.record_set.count(), before)

        # A warning (not a plain success) is surfaced to the operator.
        msgs = list(response.context["messages"])
        self.assertTrue(any(m.level == messages.WARNING and "currently lent" in m.message for m in msgs))

    def test_device_search_marks_lent_device(self):
        self._create_lent_device("EDV-LENT", "2-2", self.room_a)
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-LENT"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, 'data-lent="1"')
        # Consolidated state badge: record-type display label + lender, amber.
        self.assertContains(response, "text-bg-warning")
        self.assertContains(response, "Lent")
        self.assertContains(response, "Mustermann")

    def test_device_search_shows_record_type_badge(self):
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-MOVE"}, headers={"HX-Request": "true"}
        )
        # INROOM device -> green badge with the display label and the room number.
        self.assertContains(response, "text-bg-success")
        self.assertContains(response, "In room")
        self.assertContains(response, "A1.01")
        # The old separate "Current room" line is gone.
        self.assertNotContains(response, "Current room")

    def test_device_search_shows_single_identifier(self):
        # edv_id present -> only the EDV id is shown, not the sap_id.
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-MOVE"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "EDV-MOVE")
        self.assertNotContains(response, "1-1")

        # Only a serial number -> the SN is shown.
        sn_device = Device.objects.create(serial_number="SN-XYZ-9")
        InRoomRecord.objects.create(device=sn_device, room=self.room_a)
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "SN-XYZ-9"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "SN-XYZ-9")

    def test_device_search_uses_device_type_icon(self):
        laptop_type = DeviceType.objects.create(name="Notebook XYZ", icon="bi-laptop")
        device = Device.objects.create(edv_id="EDV-LAPTOP", device_type=laptop_type)
        InRoomRecord.objects.create(device=device, room=self.room_a)
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-LAPTOP"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "bi-laptop")

        # A device type without an icon falls back to the default.
        self.assertEqual(DeviceType(name="x").icon_class, "bi-pc-display")
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-MOVE"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "bi-pc-display")

    # --- detail link ------------------------------------------------------

    def test_search_option_carries_hidden_detail_link(self):
        # The dropdown rows ship the device detail link but hidden (revealed by JS
        # only once the device becomes the selected card).
        detail_url = reverse("assets:device_detail", kwargs={"pk": self.device.pk})
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-MOVE"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, detail_url)
        self.assertContains(response, "js-picker-detail")
        # Hidden in the option variant.
        self.assertContains(response, "js-picker-detail border-top px-3 py-1 d-none")

    def test_selected_card_shows_detail_link_visible(self):
        # On a validation re-render the selected card is server-rendered visible.
        detail_url = reverse("assets:device_detail", kwargs={"pk": self.device.pk})
        response = self.client.post(self.url, {"devices": [self.device.pk], "new_room": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, detail_url)
        self.assertContains(response, "js-picker-detail")
        self.assertNotContains(response, "js-picker-detail border-top px-3 py-1 d-none")

    # --- moveable filter --------------------------------------------------

    def test_search_excludes_removed_but_offers_ordered_devices(self):
        """An ordered device is moveable: putting it in a room is its delivery.

        A decommissioned one is not -- recovering it is a separate act with its
        own permission, offered from the admin rather than folded in here.
        """
        removed = self._create_device(edv_id="EDV-REMOVED", sap_id="3-3")
        RemovedRecord.objects.create(device=removed)
        ordered = self._create_device(edv_id="EDV-ORDERED", sap_id="4-4")
        OrderedRecord.objects.create(device=ordered)

        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "*"}, headers={"HX-Request": "true"}
        )
        self.assertNotContains(response, "EDV-REMOVED")
        self.assertContains(response, "EDV-ORDERED")
        # The plain INROOM device is still offered.
        self.assertContains(response, "EDV-MOVE")

    def test_can_relocate_ordered_device(self):
        """The counterpart to the picker: the move itself goes through."""
        ordered = self._create_device(edv_id="EDV-ORDERED", sap_id="4-4")
        OrderedRecord.objects.create(device=ordered)

        response = self.client.post(self.url, {"devices": [ordered.pk], "new_room": self.room_b.pk})
        self.assertRedirects(response, self.url)

        ordered.refresh_from_db()
        self.assertEqual(ordered.active_record.record_type, Record.INROOM)
        self.assertEqual(ordered.active_record.room, self.room_b)

    def test_search_includes_lost_device(self):
        lost = self._create_device(edv_id="EDV-LOST", sap_id="5-5")
        establish_state(LostRecord, device=lost)
        response = self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "EDV-LOST"}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "EDV-LOST")

    def test_cannot_relocate_removed_device(self):
        removed = self._create_device(edv_id="EDV-REMOVED", sap_id="3-3")
        RemovedRecord.objects.create(device=removed)
        before = removed.record_set.count()

        response = self.client.post(self.url, {"devices": [removed.pk], "new_room": self.room_b.pk})
        # The device is not in the form's queryset, so validation rejects it
        # (re-render, no redirect) and nothing is relocated.
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("devices", response.context["form"].errors)
        removed.refresh_from_db()
        self.assertEqual(removed.active_record.record_type, Record.REMOVED)
        self.assertEqual(removed.record_set.count(), before)

    def test_can_relocate_lost_device(self):
        lost = self._create_device(edv_id="EDV-LOST", sap_id="5-5")
        establish_state(LostRecord, device=lost)
        before = InRoomRecord.objects.filter(device=lost).count()

        response = self.client.post(self.url, {"devices": [lost.pk], "new_room": self.room_b.pk})
        self.assertRedirects(response, self.url)

        lost.refresh_from_db()
        self.assertEqual(lost.active_record.record_type, Record.INROOM)
        self.assertEqual(lost.active_record.room, self.room_b)
        self.assertEqual(InRoomRecord.objects.filter(device=lost).count(), before + 1)

    def test_lent_warning_shown_on_failed_post_for_lent_device(self):
        lent_device = self._create_lent_device("EDV-LENT", "2-2", self.room_a)
        response = self.client.post(self.url, {"devices": [lent_device.pk], "new_room": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please select a target room.")
        # The lent warning is rendered visible (not hidden via d-none).
        self.assertContains(response, 'id="lent-warning"')
        self.assertNotContains(response, 'id="lent-warning" class="alert alert-warning d-none"')

    def test_move_requires_device_and_room(self):
        response = self.client.post(self.url, {"devices": [], "new_room": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please select at least one device to move.")
        self.assertContains(response, "Please select a target room.")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE, LANGUAGE_CODE="en-us")
class RelocatePermissionTests(BaseTest):
    """The Move module fronts three moves with three separate permissions.

    A single coarse permission used to open it, so a user who could only mark
    lost devices as found either saw every moveable device or, once the buttons
    became permission-driven, got a "Found" button the view then refused. What is
    offered now follows from which of the three the user actually holds.
    """

    @classmethod
    def setUpTestData(cls):
        cls.room_a = Room.objects.create(number="A1.01", nickname="Office")
        cls.room_b = Room.objects.create(number="B2.02", nickname="Lab")

        # Non-superusers only ever see devices of their own tenant, so give the
        # test users one -- otherwise every assertion below would pass for the
        # wrong reason (an empty queryset rather than a missing permission).
        cls.group = Group.objects.create(name="movers")
        tenant = Tenant.objects.create(name="TestTenant")
        tenant.groups.add(cls.group)

        cls.inroom = cls()._create_device(edv_id="EDV-INROOM", sap_id="9-1")
        InRoomRecord.objects.create(device=cls.inroom, room=cls.room_a)

        cls.lost = cls()._create_device(edv_id="EDV-LOST", sap_id="9-2")
        establish_state(LostRecord, device=cls.lost)

        Device.objects.update(tenant=tenant)

    def setUp(self):
        self.url = reverse("assets:relocate")

    def _user(self, *codenames, email="mover@example.com"):
        user = get_user_model().objects.create_user(email=email, password="secret", username=email.split("@")[0])
        user.groups.add(self.group)
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="core"))
        user = get_user_model().objects.get(pk=user.pk)  # reset the perm cache
        self.client.force_login(user)
        return user

    def _search(self):
        return self.client.post(
            reverse("theme:device_search"), {"source": "move", "q_device": "*"}, headers={"HX-Request": "true"}
        )

    # --- who may open the module -----------------------------------------

    def test_a_user_with_none_of_the_moves_is_refused(self):
        self._user()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_any_one_of_the_moves_opens_the_module(self):
        self._user("transition_can_find_device")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_the_device_search_refuses_a_user_with_none_of_the_moves(self):
        self._user()
        response = self._search()
        self.assertNotContains(response, "EDV-INROOM")
        self.assertNotContains(response, "EDV-LOST")

    # --- what each of them is offered -------------------------------------

    def test_a_finder_is_offered_lost_devices_only(self):
        self._user("transition_can_find_device")
        response = self._search()
        self.assertContains(response, "EDV-LOST")
        self.assertNotContains(response, "EDV-INROOM")

    def test_a_relocator_is_not_offered_lost_devices(self):
        self._user("transition_can_relocate_device")
        response = self._search()
        self.assertContains(response, "EDV-INROOM")
        self.assertNotContains(response, "EDV-LOST")

    # --- and the move itself goes through ---------------------------------

    def test_a_finder_can_move_the_lost_device(self):
        self._user("transition_can_find_device")

        response = self.client.post(self.url, {"devices": [self.lost.pk], "new_room": self.room_b.pk})
        self.assertRedirects(response, self.url)

        self.lost.refresh_from_db()
        self.assertEqual(self.lost.active_record.record_type, Record.INROOM)
        self.assertEqual(self.lost.active_record.room, self.room_b)

    def test_a_finder_cannot_move_a_device_the_picker_never_offered(self):
        """The form shares ``move_queryset``, so POSTing a pk is not a way round it."""
        self._user("transition_can_find_device")
        before = self.inroom.record_set.count()

        response = self.client.post(self.url, {"devices": [self.inroom.pk], "new_room": self.room_b.pk})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("devices", response.context["form"].errors)
        self.assertEqual(self.inroom.record_set.count(), before)
