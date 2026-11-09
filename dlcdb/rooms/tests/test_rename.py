# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The batch rename of rooms: preview, problems, confirmation and journal."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.journal.models import JournalEntry
from dlcdb.rooms.rename import plan_renames

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

ADD_BUILDING = {"pattern": r"^(\d+)$", "replacement": r"G\1"}


def _problems(pattern, replacement):
    return {rename.old_number: (rename.new_number, rename.problem) for rename in plan_renames(pattern, replacement)}


class PlanRenamesTests(BaseTest):
    def test_only_changed_numbers_are_planned(self):
        Room.objects.create(number="235")
        Room.objects.create(number="F1.01")

        self.assertEqual(_problems(**ADD_BUILDING), {"235": ("G235", "")})

    def test_a_number_held_by_another_room_is_kept(self):
        Room.objects.create(number="235")
        Room.objects.create(number="G235")

        self.assertEqual(_problems(**ADD_BUILDING), {"235": ("G235", "Room “G235” already exists.")})

    def test_another_spelling_of_a_held_number_is_kept(self):
        # As on the add page: "g-235" and "G235" are the same number.
        Room.objects.create(number="235")
        Room.objects.create(number="g-235")

        self.assertEqual(_problems(**ADD_BUILDING), {"235": ("G235", "Room “g-235” already exists.")})

    def test_a_number_held_by_a_deactivated_room_is_kept(self):
        Room.objects.create(number="235")
        Room.objects.create(number="G235").delete()

        self.assertEqual(_problems(**ADD_BUILDING), {"235": ("G235", "Room “G235” exists, but is deactivated.")})

    def test_a_deactivated_room_is_not_renamed(self):
        Room.objects.create(number="235").delete()

        self.assertEqual(_problems(**ADD_BUILDING), {})

    def test_two_rooms_getting_the_same_number_both_keep_theirs(self):
        Room.objects.create(number="235")
        Room.objects.create(number="0235")

        problems = _problems(r"^0*(\d+)$", r"G\1")

        self.assertEqual(problems["235"], ("G235", "Another room gets the same number."))
        self.assertEqual(problems["0235"], ("G235", "Another room gets the same number."))

    def test_a_chain_of_renames_is_refused(self):
        # 1 → G1 would need G1 → GG1 first: not supported.
        Room.objects.create(number="1")
        Room.objects.create(number="G1")

        self.assertEqual(_problems(r"^(G?\d+)$", r"G\1")["1"], ("G1", "Room “G1” already exists."))

    def test_a_room_the_pattern_does_not_match_is_left_alone(self):
        # Not even trimmed: the stray space is no reason to rename it.
        Room.objects.create(number="235 ")

        self.assertEqual(_problems(**ADD_BUILDING), {})

    def test_an_empty_or_too_long_number_is_kept(self):
        Room.objects.create(number="235")

        self.assertEqual(_problems(r"^235$", ""), {"235": ("", "The new number is empty.")})
        self.assertEqual(
            _problems(r"^235$", "X" * 31),
            {"235": ("X" * 31, "The new number is longer than 30 characters.")},
        )


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class RoomRenameViewTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room_235 = Room.objects.create(number="235")
        cls.room_236 = Room.objects.create(number="236")
        cls.other_building = Room.objects.create(number="F1.01")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("rooms:rename")

    def test_index_links_the_rename_page(self):
        self.assertContains(self.client.get(reverse("rooms:index")), f'href="{self.url}"')

    def test_preview_lists_the_new_numbers_and_renames_nothing(self):
        response = self.client.get(self.url, ADD_BUILDING)

        self.assertContains(response, "G235")
        self.assertContains(response, "G236")
        self.assertContains(response, "Rename 2 rooms")
        self.assertNotContains(response, "F1.01")
        self.room_235.refresh_from_db()
        self.assertEqual(self.room_235.number, "235")

    def test_confirmation_renames_and_journals(self):
        response = self.client.post(self.url, ADD_BUILDING)

        self.assertRedirects(response, reverse("rooms:index"))
        self.room_235.refresh_from_db()
        self.other_building.refresh_from_db()
        self.assertEqual(self.room_235.number, "G235")
        self.assertEqual(self.room_235.user, self.user)
        self.assertEqual(self.other_building.number, "F1.01")

        entry = JournalEntry.objects.get(source="rooms.rename")
        self.assertEqual(entry.event, "renamed")
        self.assertEqual(entry.summary, "2 rooms renamed")
        self.assertIn("235 → G235\n236 → G236", entry.body)
        self.assertEqual(entry.user, self.user)

    def test_rooms_that_kept_their_number_are_named_on_the_room_list(self):
        Room.objects.create(number="G236")

        response = self.client.post(self.url, ADD_BUILDING, follow=True)

        # Not back to the preview: it would plan the renamed rooms once more.
        self.assertRedirects(response, reverse("rooms:index"))
        self.assertContains(response, "1 room kept its number: 236 → G236 (Room “G236” already exists.)")
        self.room_235.refresh_from_db()
        self.room_236.refresh_from_db()
        self.assertEqual(self.room_235.number, "G235")
        self.assertEqual(self.room_236.number, "236")
        self.assertIn("236 (not G236)", JournalEntry.objects.get(source="rooms.rename").body)

    def test_nothing_to_rename_writes_no_journal_entry(self):
        response = self.client.post(self.url, {"pattern": "^nomatch$", "replacement": "x"})

        self.assertRedirects(response, reverse("rooms:index"))
        self.assertFalse(JournalEntry.objects.filter(source="rooms.rename").exists())

    def test_invalid_expressions_are_form_errors(self):
        cases = [
            ({"pattern": "(", "replacement": "x"}, "Invalid regular expression"),
            ({"pattern": r"^(\d+)$", "replacement": r"G\2"}, "Invalid replacement"),
            ({"pattern": r"^(\d+)$", "replacement": r"G\g<building>"}, "Invalid replacement"),
        ]
        for data, message in cases:
            with self.subTest(data=data):
                response = self.client.post(self.url, data)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
        self.room_235.refresh_from_db()
        self.assertEqual(self.room_235.number, "235")

    def test_requires_the_change_permission(self):
        viewer = get_user_model().objects.create_user(username="viewer", email="viewer@example.com", password="x")
        viewer.user_permissions.add(Permission.objects.get(codename="view_room", content_type__app_label="core"))
        self.client.force_login(viewer)

        self.assertNotContains(self.client.get(reverse("rooms:index")), f'href="{self.url}"')
        self.assertEqual(self.client.get(self.url, ADD_BUILDING).status_code, 403)
        self.assertEqual(self.client.post(self.url, ADD_BUILDING).status_code, 403)
        self.room_235.refresh_from_db()
        self.assertEqual(self.room_235.number, "235")
