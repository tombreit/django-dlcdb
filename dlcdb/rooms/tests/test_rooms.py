# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the standalone Room frontend."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, Room
from dlcdb.core.tests.basetest import BaseTest


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
