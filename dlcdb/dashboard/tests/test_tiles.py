# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The dashboard tiles carry the class names their styling and future JS hang on."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import Device, DeviceType, InRoomRecord, Room

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DashboardTileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="tiles@example.com", password="secret")

        # A device type with a note, so the note badge renders too.
        cls.device_type = DeviceType.objects.create(name="Notebook", prefix="NTB", note="a note")
        cls.room = Room.objects.create(number="T1.01")
        device = Device.objects.create(edv_id="TILE-1", sap_id="7001-1", device_type=cls.device_type)
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

    def test_the_note_badge_is_targetable(self):
        """Rendered only for a model with notes, hence the device type seeded above."""
        self.assertContains(self.client.get(reverse("dashboard:index")), "dashboard-tile-badge")

    def test_a_tile_is_still_a_link_wearing_the_card_utilities(self):
        """The new names are additive: the Bootstrap classes and the href must survive."""
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, 'class="dashboard-tile card h-100 text-decoration-none text-reset text-center"')
        self.assertContains(response, f'href="{reverse("assets:device_index")}"')
