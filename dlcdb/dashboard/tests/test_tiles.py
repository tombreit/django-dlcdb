# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The dashboard tiles: their two groups, values and captions, and the class names their styling hangs on."""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import (
    Device,
    DeviceType,
    InRoomRecord,
    Inventory,
    LentRecord,
    LicenceRecord,
    LostRecord,
    Record,
    Room,
)
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def _tiles(response):
    """All tiles, in page order: the attention group, then the stock group."""
    return response.context["attention_tiles"] + response.context["stock_tiles"]


def _tile(response, url):
    return next(tile for tile in _tiles(response) if tile["url"] == url)


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
            return _tile(response, "assets:device_index")["value"]

        self.assertEqual(device_tile_count(self.client.get(reverse("dashboard:index"))), 1)

        no_tenant = get_user_model().objects.create_user(
            username="no-tenant", email="no-tenant@example.com", password="secret"
        )
        self.client.force_login(no_tenant)
        self.assertEqual(device_tile_count(self.client.get(reverse("dashboard:index"))), 0)

    def test_notes_are_a_caption(self):
        """Rendered only for a model with notes, hence the device type seeded above."""
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(_tile(response, "assets:device_type_index")["caption"], "1 with note")
        self.assertContains(response, '<div class="dashboard-tile-caption">1 with note</div>', html=True)

    def test_the_journal_tile_counts_problems_and_links_to_the_journal(self):
        JournalEntry.objects.log(
            source="pytest.topic", event="failed", summary="Broke", level=JournalEntry.Level.ERROR, tenant=self.tenant
        )

        response = self.client.get(reverse("dashboard:index"))
        journal = _tile(response, "journal:index")

        self.assertIn((JournalEntry.Level.ERROR, 1), journal["level_counts"])
        self.assertEqual(journal["query_params"], "")
        self.assertContains(response, "dashboard-tile-levels")

    def test_a_tile_is_still_a_link_wearing_the_card_utilities(self):
        """The new names are additive: the Bootstrap classes and the href must survive."""
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, 'class="dashboard-tile card h-100 text-decoration-none text-reset"')
        self.assertContains(response, f'href="{reverse("assets:device_index")}"')

    def test_tiles_come_in_two_groups(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(
            [tile["url"] for tile in response.context["attention_tiles"]],
            ["lending:index", "assets:record_index", "journal:index"],
        )
        self.assertEqual(
            [tile["url"] for tile in response.context["stock_tiles"]],
            [
                "assets:device_index",
                "lending:index",
                "rooms:index",
                "assets:device_type_index",
                "licenses:index",
                "smallstuff:person_search",
            ],
        )
        self.assertContains(response, "Needs attention")
        self.assertContains(response, "Stock")

    def test_a_count_other_than_one_takes_the_plural_label(self):
        """Nothing counted is "0 licences", not "0 licence"."""
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(_tile(response, "licenses:index")["value"], 0)
        self.assertEqual(_tile(response, "licenses:index")["label"], LicenceRecord._meta.verbose_name_plural)
        self.assertEqual(_tile(response, "assets:device_index")["label"], Device._meta.verbose_name)

    def test_the_lendings_tile_shows_the_lent_count_out_of_the_lendable_devices(self):
        lendable = Device.objects.create(
            edv_id="TILE-LEND", sap_id="7001-2", device_type=self.device_type, tenant=self.tenant, is_lentable=True
        )
        InRoomRecord.objects.create(device=lendable, room=self.room)
        lent = Device.objects.create(
            edv_id="TILE-LENT", sap_id="7001-3", device_type=self.device_type, tenant=self.tenant, is_lentable=True
        )
        establish_state(LentRecord, device=lent, room=self.room, lent_desired_end_date=datetime.date(2099, 1, 1))

        stock = self.client.get(reverse("dashboard:index")).context["stock_tiles"]
        lendings = next(tile for tile in stock if tile["url"] == "lending:index")

        self.assertEqual(lendings["value"], 1)
        self.assertEqual(lendings["caption"], "of 2 lendable")

    def test_the_overdue_tile_is_tinted_only_when_something_is_overdue(self):
        def overdue_tile():
            attention = self.client.get(reverse("dashboard:index")).context["attention_tiles"]
            return next(tile for tile in attention if tile["url"] == "lending:index")

        self.assertEqual((overdue_tile()["value"], overdue_tile()["tone"]), (0, ""))

        device = Device.objects.create(
            edv_id="TILE-LATE", sap_id="7001-4", device_type=self.device_type, tenant=self.tenant, is_lentable=True
        )
        establish_state(LentRecord, device=device, room=self.room, lent_desired_end_date=datetime.date(2020, 1, 1))

        self.assertEqual((overdue_tile()["value"], overdue_tile()["tone"]), (1, "warning"))
        self.assertContains(self.client.get(reverse("dashboard:index")), "dashboard-tile-warning")

    def test_an_active_inventory_adds_a_progress_tile(self):
        Inventory.objects.create(name="2026", is_active=True)

        response = self.client.get(reverse("dashboard:index"))
        inventory = _tile(response, "inventory:inventorize-room-list")

        self.assertEqual((inventory["value"], inventory["unit"], inventory["progress"]), (0, "%", 0))
        self.assertEqual(inventory["caption"], "0 of 1 devices")
        self.assertContains(response, "dashboard-tile-progress")


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
        return _tiles(self.client.get(reverse("dashboard:index")))

    def test_no_tile_links_into_the_django_admin(self):
        self.assertEqual([tile for tile in self._tiles() if tile["url"].startswith("admin:")], [])

    def test_rooms_and_device_types_point_at_their_frontends(self):
        urls = [tile["url"] for tile in self._tiles()]

        self.assertIn("rooms:index", urls)
        self.assertIn("assets:device_type_index", urls)

    def test_the_lost_tile_scopes_the_record_list_to_lost_records(self):
        lost = next(tile for tile in self._tiles() if tile["url"] == "assets:record_index")

        self.assertIn(f"record_type={Record.LOST}", lost["query_params"])

    def test_a_note_count_adds_the_note_filter_to_the_link(self):
        lost = next(tile for tile in self._tiles() if tile["url"] == "assets:record_index")

        self.assertTrue(lost["show_notes"])
        self.assertIn("has_note=has_note", lost["query_params"])

    def test_a_tile_without_a_note_count_carries_no_note_filter(self):
        """Otherwise the link promises a filter the tile never advertised."""
        for tile in self._tiles():
            if not tile["show_notes"]:
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
