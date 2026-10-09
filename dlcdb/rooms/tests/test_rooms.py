# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the standalone Room frontend."""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, LentRecord, LostRecord, Person, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.tenants.models import Tenant

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class RoomFrontendTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.server_room = Room.objects.create(number="F1.01", nickname="Server room", note="Keep cool")
        cls.plain_room = Room.objects.create(number="F2.02")

    def setUp(self):
        self.client.force_login(self.user)
        self.index_url = reverse("rooms:index")

    def _core_perm_user(self, *codenames):
        """A plain user holding exactly the given core permissions."""
        user = get_user_model().objects.create_user(
            username="room-operator", email="operator@example.com", password="secret"
        )
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="core"))
        return user

    def test_index_renders_room_table(self):
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<table")
        self.assertContains(response, "F1.01")
        self.assertContains(response, "Server room")
        self.assertContains(response, "Add room")

    def test_index_htmx_response_is_fragment_only(self):
        response = self.client.get(self.index_url, headers={"HX-Request": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="room-list"')
        self.assertNotContains(response, "<html")

    def test_search_filter(self):
        response = self.client.get(self.index_url, {"search": "Server"}, headers={"HX-Request": "true"})
        self.assertContains(response, "F1.01")
        self.assertNotContains(response, "F2.02")

    def test_has_note_filter(self):
        response = self.client.get(self.index_url, {"has_note": "has_note"}, headers={"HX-Request": "true"})
        self.assertContains(response, "F1.01")
        self.assertNotContains(response, "F2.02")

        response = self.client.get(self.index_url, {"has_note": "has_no_note"}, headers={"HX-Request": "true"})
        self.assertContains(response, "F2.02")
        self.assertNotContains(response, "F1.01")

    def test_index_shows_active_record_count(self):
        device = self._create_device(edv_id="EDV-ROOMED", sap_id="1-1")
        InRoomRecord.objects.create(device=device, room=self.server_room)

        response = self.client.get(self.index_url, {"search": "F1.01"}, headers={"HX-Request": "true"})
        self.assertContains(response, '<span class="badge text-bg-light border">1</span>', html=False)

    def test_create_room_sets_audit_user_and_qrcode(self):
        response = self.client.post(reverse("rooms:add"), {"number": "F3.03", "nickname": "New room"})

        room = Room.objects.get(number="F3.03")
        self.assertRedirects(response, reverse("rooms:detail", args=[room.pk]))
        self.assertEqual(room.user, self.user)
        self.assertTrue(room.qrcode)

    def test_edit_room_returns_to_the_filtered_index(self):
        url = reverse("rooms:detail", args=[self.plain_room.pk]) + "?next=search%3DF2"
        response = self.client.post(url, {"number": "F2.02", "nickname": "Renamed"})

        self.assertRedirects(response, f"{self.index_url}?search=F2")
        self.plain_room.refresh_from_db()
        self.assertEqual(self.plain_room.nickname, "Renamed")

    def test_auto_return_room_stays_unique_after_frontend_edit(self):
        self.server_room.is_auto_return_room = True
        self.server_room.save()

        self.client.post(
            reverse("rooms:detail", args=[self.plain_room.pk]),
            {"number": "F2.02", "is_auto_return_room": "on"},
        )

        self.server_room.refresh_from_db()
        self.plain_room.refresh_from_db()
        self.assertTrue(self.plain_room.is_auto_return_room)
        self.assertFalse(self.server_room.is_auto_return_room)

    def test_detail_sidebar_links_devices_and_collapses_the_qr_card(self):
        device = self._create_device(edv_id="EDV-SIDEBAR", sap_id="9-9")
        InRoomRecord.objects.create(device=device, room=self.server_room)

        response = self.client.get(reverse("rooms:detail", args=[self.server_room.pk]))

        # Device count links to the device index filtered by this room.
        self.assertContains(response, f"{reverse('assets:device_index')}?active_record__room={self.server_room.pk}")
        self.assertContains(response, "1 device in this room")
        # The QR card is a native <details> without `open` (collapsed) and last.
        self.assertContains(response, '<details class="card mb-3 card-collapse">')
        self.assertNotContains(response, "<details open")

    def test_view_only_user_gets_readonly_detail_and_cannot_post(self):
        self.client.force_login(self._core_perm_user("view_room"))
        url = reverse("rooms:detail", args=[self.server_room.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<form method="post"')

        denied = self.client.post(url, {"number": "F1.01"})
        self.assertEqual(denied.status_code, 403)

    def test_index_requires_view_permission(self):
        self.client.force_login(self._core_perm_user())
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 403)

    def test_reconcile_url_lives_in_the_rooms_namespace(self):
        self.assertEqual(reverse("rooms:reconcile", args=[1]), "/rooms/reconcile/1/")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class RoomChangesTests(BaseTest):
    """The stock changes card on the room detail page: devices that arrived or left."""

    def setUp(self):
        user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        self.client.force_login(self._join_default_tenant(user))
        self.mover = get_user_model().objects.create_user(username="mover", email="mover@example.com")
        self.room = Room.objects.create(number="F1.01")
        self.other_room = Room.objects.create(number="F2.02")
        self.url = reverse("rooms:detail", args=[self.room.pk])

    def _record(self, proxy_model, device, **fields):
        """A record written by the mover, without transition checks (like imported data)."""
        return establish_state(proxy_model, device=device, user=self.mover, **fields)

    def test_located_device_arrived_and_names_who_recorded_it(self):
        device = self._create_device(edv_id="EDV-HERE")
        record = self._record(InRoomRecord, device, room=self.room)

        response = self.client.get(self.url)
        self.assertContains(response, "Arrived")
        self.assertContains(response, "mover@example.com")
        self.assertContains(response, reverse("assets:device_detail", args=[device.pk]))
        self.assertContains(response, reverse("assets:record_detail", args=[record.pk]))

    def test_moved_device_left_for_the_other_room_and_arrived_there(self):
        device = self._create_device(edv_id="EDV-MOVED")
        self._record(InRoomRecord, device, room=self.room)
        move = self._record(InRoomRecord, device, room=self.other_room)

        response = self.client.get(self.url)
        self.assertContains(response, "Left")
        self.assertContains(response, f'href="{reverse("rooms:detail", args=[self.other_room.pk])}"')
        self.assertContains(response, reverse("assets:record_detail", args=[move.pk]))

        response = self.client.get(reverse("rooms:detail", args=[self.other_room.pk]))
        self.assertContains(response, "Arrived")
        self.assertContains(response, f'href="{self.url}"')

    def test_consecutive_records_in_the_room_are_one_arrival(self):
        device = self._create_device(edv_id="EDV-STAMPED")
        first = self._record(InRoomRecord, device, room=self.room)
        # What an inventory stamp used to leave behind: a copy of the active record.
        copy = self._record(InRoomRecord, device, room=self.room)

        response = self.client.get(self.url)
        self.assertContains(response, "EDV-STAMPED", count=1)
        self.assertContains(response, reverse("assets:record_detail", args=[first.pk]))
        self.assertNotContains(response, reverse("assets:record_detail", args=[copy.pk]))

    def test_lost_device_left_without_a_room(self):
        device = self._create_device(edv_id="EDV-LOST")
        self._record(InRoomRecord, device, room=self.room)
        lost = self._record(LostRecord, device)

        response = self.client.get(self.url)
        self.assertContains(response, "Marked as not locatable")
        self.assertContains(response, reverse("assets:record_detail", args=[lost.pk]))

    def test_device_lent_elsewhere_names_the_borrower(self):
        device = self._create_device(edv_id="EDV-LENT")
        self._record(InRoomRecord, device, room=self.room)
        self._record(
            LentRecord,
            device,
            person=Person.objects.create(first_name="Erika", last_name="Musterfrau", email="erika@example.com"),
            room=self.other_room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("rooms:detail", args=[self.other_room.pk])}"')
        self.assertContains(response, "Musterfrau, Erika")

    def test_device_lent_without_a_room_is_listed(self):
        # Old lendings were stored without a room.
        device = self._create_device(edv_id="EDV-LENT-NOWHERE")
        self._record(InRoomRecord, device, room=self.room)
        self._record(
            LentRecord,
            device,
            person=Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com"),
            lent_start_date=datetime.date(2016, 1, 1),
            lent_desired_end_date=datetime.date(2016, 6, 1),
        )

        response = self.client.get(self.url, {"show_all": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mustermann, Max")

    def test_device_of_another_tenant_is_hidden(self):
        device = self._create_device(edv_id="EDV-FOREIGN", tenant=Tenant.objects.create(name="Other tenant"))
        self._record(InRoomRecord, device, room=self.room)

        self.assertNotContains(self.client.get(self.url), "EDV-FOREIGN")

    def test_room_without_changes_says_so(self):
        self.assertContains(self.client.get(self.url), "No device has arrived in or left this room yet.")

    def test_pager_swaps_only_the_card_newest_first(self):
        for number in range(26):
            self._record(InRoomRecord, self._create_device(edv_id=f"EDV-{number:02}"), room=self.room)

        response = self.client.get(self.url, {"page": 2}, headers={"HX-Request": "true"})
        self.assertContains(response, 'id="room-changes"')
        self.assertNotContains(response, "<html")
        self.assertContains(response, "EDV-00")
        self.assertNotContains(response, "EDV-25")

    def test_card_needs_the_record_view_permission(self):
        viewer = get_user_model().objects.create_user(username="room-viewer", email="viewer@example.com")
        viewer.user_permissions.add(Permission.objects.get(codename="view_room", content_type__app_label="core"))
        self.client.force_login(viewer)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="room-changes"')
