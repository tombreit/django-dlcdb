# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The record trail's note filter.

``has_note`` mirrors the room and device-type list views (and the admin's
HasNoteFilter). The dashboard's "Lost" tile links here with
``?record_type=LOST``, adding ``has_note=has_note`` when it shows its note badge,
so both parameters have to bite together.

Exercised against the FilterSet rather than the rendered list: a row shows its
*device*, and a device usually owns several records, so asserting on markup
cannot tell "this record has a note" from "this device has another record".
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, LostRecord, Record, Room
from dlcdb.core.tests.basetest import BaseTest

from ..filters import RecordFilter

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class RecordNoteFilterTests(BaseTest, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.room = Room.objects.create(number="R1.01")

        # A device must be located before it can go missing (dlcdb.core.lifecycle),
        # so each one carries an InRoomRecord too. Those are noteless, which is
        # what makes "filter the records, not the devices" observable.
        noted_device = cls()._create_device(edv_id="REC-NOTED", sap_id="8001")
        InRoomRecord.objects.create(device=noted_device, room=cls.room)
        cls.noted_lost = LostRecord.objects.create(device=noted_device, note="Vanished after the move")

        plain_device = cls()._create_device(edv_id="REC-PLAIN", sap_id="8002")
        InRoomRecord.objects.create(device=plain_device, room=cls.room)
        cls.plain_lost = LostRecord.objects.create(device=plain_device)

    @staticmethod
    def _filtered(**params):
        return RecordFilter(params, queryset=Record.objects.all()).qs

    def test_has_note_keeps_only_records_carrying_a_note(self):
        self.assertEqual(list(self._filtered(has_note="has_note")), [self.noted_lost])

    def test_has_no_note_is_the_complement(self):
        noted = set(self._filtered(has_note="has_note"))
        unnoted = set(self._filtered(has_note="has_no_note"))

        self.assertNotIn(self.noted_lost, unnoted)
        self.assertIn(self.plain_lost, unnoted)
        self.assertEqual(noted | unnoted, set(Record.objects.all()))

    def test_an_unset_note_filter_keeps_everything(self):
        self.assertEqual(self._filtered().count(), Record.objects.count())

    def test_the_note_filter_combines_with_record_type(self):
        """The exact pair the dashboard's Lost tile links with."""
        self.assertEqual(
            list(self._filtered(record_type=Record.LOST, has_note="has_note")),
            [self.noted_lost],
        )

    def test_record_type_alone_matches_what_the_lost_tile_counts(self):
        """The tile counts LostRecord.objects; the link must not show a different set."""
        self.assertEqual(
            set(self._filtered(record_type=Record.LOST)),
            set(LostRecord.objects.all()),
        )


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class RecordDetailDeviceLinkTests(BaseTest, TestCase):
    """The record page links its device like its room and lender: only for a user who may open it."""

    @classmethod
    def setUpTestData(cls):
        device = cls()._create_device(edv_id="REC-LINK", sap_id="8100")
        record = InRoomRecord.objects.create(device=device, room=Room.objects.create(number="R2.02"))
        cls.device_url = reverse("assets:device_detail", args=[device.pk])
        cls.record_url = reverse("assets:record_detail", args=[record.pk])

    def _login_with(self, *codenames):
        user = get_user_model().objects.create_user(
            username="record-viewer", email="viewer@example.com", password="secret"
        )
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=codenames))
        self._join_default_tenant(user)
        self.client.force_login(user)

    def test_the_device_ids_link_to_the_device(self):
        self._login_with("view_record", "view_device")

        response = self.client.get(self.record_url)

        self.assertContains(response, f'<a href="{self.device_url}">REC-LINK</a>', html=True)
        self.assertContains(response, f'<a href="{self.device_url}">8100</a>', html=True)

    def test_without_view_device_no_link_leads_to_the_device(self):
        self._login_with("view_record")

        response = self.client.get(self.record_url)

        self.assertContains(response, "REC-LINK")
        self.assertNotContains(response, self.device_url)
