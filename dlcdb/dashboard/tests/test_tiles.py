# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The dashboard tiles carry the class names their styling and future JS hang on."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import Device, DeviceType, InRoomRecord, LostRecord, Record, Room
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def _tenant_of(user, name):
    """A tenant the user sees: superusers too see only the tenants of their groups."""
    tenant = Tenant.objects.create(name=name)
    group = Group.objects.create(name=name)
    tenant.groups.add(group)
    user.groups.add(group)
    return tenant


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DashboardTileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="tiles@example.com", password="secret")

        # A device type with a note, so the note badge renders too.
        cls.device_type = DeviceType.objects.create(name="Notebook", prefix="NTB", note="a note")
        cls.room = Room.objects.create(number="T1.01")
        cls.tenant = _tenant_of(cls.user, "Tiles")
        device = Device.objects.create(edv_id="TILE-1", sap_id="7001-1", device_type=cls.device_type, tenant=cls.tenant)
        InRoomRecord.objects.create(device=device, room=cls.room)

    def setUp(self):
        self.client.force_login(self.user)

    def test_the_tile_grid_and_tiles_are_targetable(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, "dashboard-tiles")
        self.assertContains(response, "dashboard-tile ")
        self.assertContains(response, "dashboard-tile-count")
        self.assertContains(response, "dashboard-tile-label")
        self.assertContains(response, "dashboard-tile-icon")

    def test_counts_are_scoped_to_the_users_tenants(self):
        """A user without tenant sees zeros, not the global numbers."""

        def device_tile_count(response):
            return next(tile["count"] for tile in response.context["tiles"] if tile["url"] == "assets:device_index")

        self.assertEqual(device_tile_count(self.client.get(reverse("dashboard:index"))), 1)

        no_tenant = get_user_model().objects.create_user(
            username="no-tenant", email="no-tenant@example.com", password="secret"
        )
        self.client.force_login(no_tenant)
        self.assertEqual(device_tile_count(self.client.get(reverse("dashboard:index"))), 0)

    def test_the_note_badge_is_targetable(self):
        """Rendered only for a model with notes, hence the device type seeded above."""
        self.assertContains(self.client.get(reverse("dashboard:index")), "dashboard-tile-badge")

    def test_the_journal_tile_counts_problems_and_links_to_the_journal(self):
        JournalEntry.objects.log(
            source="pytest.topic", event="failed", summary="Broke", level=JournalEntry.Level.ERROR, tenant=self.tenant
        )

        response = self.client.get(reverse("dashboard:index"))
        journal = next(tile for tile in response.context["tiles"] if tile["url"] == "journal:index")

        self.assertIn((JournalEntry.Level.ERROR, 1), journal["level_counts"])
        self.assertEqual(journal["query_params"], "")
        self.assertContains(response, "dashboard-tile-levels")

    def test_a_tile_is_still_a_link_wearing_the_card_utilities(self):
        """The new names are additive: the Bootstrap classes and the href must survive."""
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, 'class="dashboard-tile card h-100 text-decoration-none text-reset text-center"')
        self.assertContains(response, f'href="{reverse("assets:device_index")}"')


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DashboardTileTargetTests(TestCase):
    """Where the tiles point.

    The tiles were the last place linking into the admin changelists that the
    frontend apps (rooms, device types, records) have since replaced.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="targets@example.com", password="secret")
        cls.room = Room.objects.create(number="T2.01")
        cls.device_type = DeviceType.objects.create(name="Beamer", prefix="BMR")

        # A lost record carrying a note, so the Lost tile shows its badge and
        # therefore appends the note filter to its link.
        device = Device.objects.create(
            edv_id="TILE-LOST", sap_id="7002-1", device_type=cls.device_type, tenant=_tenant_of(cls.user, "Targets")
        )
        InRoomRecord.objects.create(device=device, room=cls.room)
        LostRecord.objects.create(device=device, note="Not at its desk")

    def setUp(self):
        self.client.force_login(self.user)

    def _tiles(self):
        return self.client.get(reverse("dashboard:index")).context["tiles"]

    def test_no_tile_links_into_the_django_admin(self):
        self.assertEqual([tile for tile in self._tiles() if tile["url"].startswith("admin:")], [])

    def test_rooms_and_device_types_point_at_their_frontends(self):
        urls = [tile["url"] for tile in self._tiles()]

        self.assertIn("rooms:index", urls)
        self.assertIn("assets:device_type_index", urls)

    def test_the_lost_tile_scopes_the_record_list_to_lost_records(self):
        lost = next(tile for tile in self._tiles() if tile["url"] == "assets:record_index")

        self.assertIn(f"record_type={Record.LOST}", lost["query_params"])

    def test_a_note_badge_adds_the_note_filter_to_the_link(self):
        lost = next(tile for tile in self._tiles() if tile["url"] == "assets:record_index")

        self.assertTrue(lost["show_badge"])
        self.assertIn("has_note=has_note", lost["query_params"])

    def test_a_tile_without_a_badge_carries_no_note_filter(self):
        """Otherwise the link promises a filter the tile never advertised."""
        for tile in self._tiles():
            if not tile["show_badge"]:
                self.assertNotIn("has_note", tile["query_params"])

    def test_every_tile_link_is_accepted_by_its_target(self):
        """Follow each tile's href for real.

        The Lost tile's old admin link was already broken: it appended
        has_note=has_note, which LostRecordAdmin does not register as a list
        filter, so the admin bounced it to ?e=1.
        """
        for tile in self._tiles():
            url = reverse(tile["url"])
            if tile["query_params"]:
                url = f"{url}?{tile['query_params']}"
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("e=1", response.request["QUERY_STRING"])

    def test_every_tile_renders_regardless_of_permissions(self):
        """Tiles are deliberately not permission-filtered; a click may 403."""
        as_superuser = [tile["url"] for tile in self._tiles()]

        stranger = get_user_model().objects.create_user(
            username="tile-stranger", email="stranger@example.com", password="secret"
        )
        self.client.force_login(stranger)
        as_stranger = [tile["url"] for tile in self._tiles()]

        self.assertTrue(as_superuser)
        self.assertEqual(as_stranger, as_superuser)
