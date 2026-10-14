# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The device page's own forms for Not locatable, Remove, Restore and Recover."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from django.utils.html import escape

from dlcdb.assets.views.devices import TRANSITION_FORMS
from dlcdb.core import lifecycle
from dlcdb.core.models import InRoomRecord, Record, RemovedRecord, Room
from dlcdb.core.models.record import SCRAPPED
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.tenants.models import Tenant
from dlcdb.theme.device_state import RELOCATE_TRANSITIONS
from dlcdb.theme.navigation import with_back

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def test_every_transition_has_a_frontend_screen():
    """The forms here serve exactly the transitions without a screen of their own."""
    own_screens = RELOCATE_TRANSITIONS | {"order", "lend", "return_lending"}
    assert set(TRANSITION_FORMS) == set(lifecycle.BY_NAME) - own_screens


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DeviceTransitionTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.room = Room.objects.create(number="A1.01")

    def _login(self, *transitions, username="worker"):
        """A non-staff user of the default tenant who may view devices and make these moves."""
        user = get_user_model().objects.create_user(
            username=username, email=f"{username}@example.com", password="secret"
        )
        self._join_default_tenant(user)
        user.user_permissions.add(Permission.objects.get(codename="view_device", content_type__app_label="core"))
        for name in transitions:
            app_label, codename = lifecycle.BY_NAME[name].permission.split(".")
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label=app_label))
        self.client.force_login(user)
        return user

    def _located_device(self, **fields):
        device = self._create_device(**fields)
        InRoomRecord.objects.create(device=device, room=self.room)
        device.refresh_from_db()
        return device

    @staticmethod
    def _url(device, name):
        return reverse("assets:device_transition", args=[device.pk, name])

    def test_a_non_staff_user_removes_a_device_with_just_the_remove_permission(self):
        """The reported case: no Staff flag, no add_removedrecord, only the transition."""
        user = self._login("remove")
        device = self._located_device()
        detail_url = reverse("assets:device_detail", args=[device.pk])

        self.assertContains(self.client.get(detail_url), f'href="{self._url(device, "remove")}"')
        self.assertEqual(self.client.get(self._url(device, "remove")).status_code, 200)
        response = self.client.post(
            self._url(device, "remove"), {"disposition_state": SCRAPPED, "removed_info": "Recycling yard"}
        )

        self.assertRedirects(response, detail_url)
        device.refresh_from_db()
        record = device.active_record
        self.assertEqual(record.record_type, Record.REMOVED)
        self.assertEqual(record.disposition_state, SCRAPPED)
        self.assertEqual(record.removed_info, "Recycling yard")
        self.assertEqual(record.user, user)

    def test_not_locatable_restore_and_recover_need_only_their_own_permission(self):
        cases = [
            ("lose", InRoomRecord, {"note": "Not in its room"}, Record.LOST),
            ("restore", RemovedRecord, {"note": "Removed by mistake"}, Record.LOST),
            ("recover", RemovedRecord, {"room": self.room.pk, "note": "Found in the basement"}, Record.INROOM),
        ]
        for name, starting_record, data, target in cases:
            with self.subTest(name):
                self._login(name, username=f"worker-{name}")
                device = self._create_device()
                establish_state(starting_record, device=device, room=self.room)

                response = self.client.post(self._url(device, name), data)

                self.assertRedirects(response, reverse("assets:device_detail", args=[device.pk]))
                device.refresh_from_db()
                self.assertEqual(device.active_record.record_type, target)
                self.assertEqual(device.active_record.note, data["note"])

    def test_without_the_transition_permission_the_form_is_forbidden(self):
        self._login("lose")
        device = self._located_device()

        self.assertEqual(self.client.get(self._url(device, "remove")).status_code, 403)
        self.assertEqual(self.client.post(self._url(device, "remove"), {}).status_code, 403)
        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.INROOM)

    def test_a_device_of_another_tenant_is_not_found(self):
        self._login("remove")
        device = self._create_device(tenant=Tenant.objects.create(name="Foreign tenant"))

        self.assertEqual(self.client.get(self._url(device, "remove")).status_code, 404)

    def test_an_illegal_state_change_is_refused_without_a_record(self):
        self._login("restore")
        device = self._located_device()
        record_count = device.record_set.count()

        response = self.client.post(self._url(device, "restore"), {"note": "?"}, follow=True)

        self.assertRedirects(response, reverse("assets:device_detail", args=[device.pk]))
        self.assertContains(response, "is not allowed for a device in state")
        self.assertEqual(device.record_set.count(), record_count)

    def test_a_transition_without_a_form_here_is_not_found(self):
        """Order, Move and Lend have their own screens; unknown names do not exist."""
        self._login("order", "relocate")
        device = self._located_device()

        for name in ("order", "relocate", "fly"):
            with self.subTest(name):
                self.assertEqual(self.client.get(self._url(device, name)).status_code, 404)

    def test_recover_needs_a_room(self):
        self._login("recover")
        device = self._create_device()
        establish_state(RemovedRecord, device=device)

        response = self.client.post(self._url(device, "recover"), {"note": "No room given"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["room"])
        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.REMOVED)

    def test_the_form_returns_to_the_back_url_of_the_screen_that_offered_it(self):
        self._login("lose")
        device = self._located_device()
        back = "/inventory/devices/?q=EDV"
        url = with_back(self._url(device, "lose"), back)

        self.assertContains(self.client.get(url), f'href="{escape(back)}"')
        response = self.client.post(url, {"note": "Not in its room"})

        self.assertRedirects(response, back, fetch_redirect_response=False)
        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.LOST)

    def test_order_returns_to_the_back_url(self):
        self._login("order")
        device = self._create_device()
        back = "/inventory/devices/"

        response = self.client.post(with_back(reverse("assets:device_order", args=[device.pk]), back))

        self.assertRedirects(response, back, fetch_redirect_response=False)
        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.ORDERED)

    def test_a_back_url_off_this_site_is_ignored(self):
        self._login("lose")
        device = self._located_device()

        response = self.client.post(with_back(self._url(device, "lose"), "https://evil.example/"), {"note": "?"})

        self.assertRedirects(response, reverse("assets:device_detail", args=[device.pk]))

    def test_anonymous_users_are_sent_to_the_login(self):
        device = self._located_device()

        response = self.client.get(self._url(device, "remove"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(settings.LOGIN_URL))
