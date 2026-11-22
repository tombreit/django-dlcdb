# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The record trail's note filter.

``has_note`` mirrors the room and device-type list views (and the admin's
HasNoteFilter). The dashboard's "Missing" tile links here with
``?record_type=LOST&is_active=true``, so that pair must show what the tile counts.

Exercised against the FilterSet rather than the rendered list: a row shows its
*device*, and a device usually owns several records, so asserting on markup
cannot tell "this record has a note" from "this device has another record".
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from dlcdb.core.models import Attachment, InRoomRecord, LostRecord, Person, Record, RemovedRecord, Room
from dlcdb.core.tests.basetest import BaseTest

from ..filters import RecordFilter


def _login_with(test, *codenames):
    """Log the test's client in as a user of the default tenant with these core permissions."""
    user = get_user_model().objects.create_user(username="record-viewer", email="viewer@example.com", password="secret")
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=codenames))
    test._join_default_tenant(user)
    test.client.force_login(user)
    return user


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
        self.assertEqual(
            list(self._filtered(record_type=Record.LOST, has_note="has_note")),
            [self.noted_lost],
        )

    def test_the_lost_tiles_link_matches_what_it_counts(self):
        """The tile counts the current LOST records; a device found again drops out of both."""
        found_device = self._create_device(edv_id="REC-FOUND", sap_id="8003")
        InRoomRecord.objects.create(device=found_device, room=self.room)
        found_lost = LostRecord.objects.create(device=found_device)
        InRoomRecord.objects.create(device=found_device, room=self.room)

        shown = set(self._filtered(record_type=Record.LOST, is_active="true"))

        self.assertEqual(shown, set(LostRecord.objects.filter(is_active=True)))
        self.assertNotIn(found_lost, shown)


class RecordSearchTests(BaseTest, TestCase):
    def test_search_matches_the_records_person(self):
        room = Room.objects.create(number="R1.02")
        person = Person.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.org")
        with_person = InRoomRecord.objects.create(
            device=self._create_device(edv_id="REC-ADA", sap_id="8003"), room=room, person=person
        )
        InRoomRecord.objects.create(device=self._create_device(edv_id="REC-NOBODY", sap_id="8004"), room=room)

        found = RecordFilter({"search": "ada@example"}, queryset=Record.objects.all()).qs

        self.assertEqual(list(found), [with_person])


class RecordDetailDeviceLinkTests(BaseTest, TestCase):
    """The record page links its device like its room and lender: only for a user who may open it."""

    @classmethod
    def setUpTestData(cls):
        device = cls()._create_device(edv_id="REC-LINK", sap_id="8100")
        record = InRoomRecord.objects.create(device=device, room=Room.objects.create(number="R2.02"))
        cls.device_url = reverse("assets:device_detail", args=[device.pk])
        cls.record_url = reverse("assets:record_detail", args=[record.pk])

    def test_the_device_ids_link_to_the_device(self):
        _login_with(self, "view_record", "view_device")

        response = self.client.get(self.record_url)

        self.assertContains(response, f'<a href="{self.device_url}">REC-LINK</a>', html=True)
        self.assertContains(response, f'<a href="{self.device_url}">8100</a>', html=True)

    def test_without_view_device_no_link_leads_to_the_device(self):
        _login_with(self, "view_record")

        response = self.client.get(self.record_url)

        self.assertContains(response, "REC-LINK")
        self.assertNotContains(response, self.device_url)


class RecordAttachmentTests(BaseTest, TestCase):
    """Files are attached in the record page's Attachments card, also to a record saved long before."""

    @classmethod
    def setUpTestData(cls):
        cls.record = RemovedRecord.objects.create(device=cls()._create_device(edv_id="REC-REMOVED", sap_id="8200"))
        cls.record_url = reverse("assets:record_detail", args=[cls.record.pk])
        cls.card_url = reverse("assets:record_attachments", args=[cls.record.pk])

    def _upload(self):
        photo = SimpleUploadedFile("damage.png", b"\x89PNG", content_type="image/png")
        return self.client.post(self.card_url, {"title": "Housing damage", "file": photo})

    def test_add_attachment_swaps_in_the_upload_form(self):
        _login_with(self, "view_record", "add_attachment")

        self.assertContains(self.client.get(self.record_url), f'hx-get="{self.card_url}?form"')
        self.assertContains(self.client.get(f"{self.card_url}?form"), 'type="file"')

    def test_a_saved_upload_is_the_cards_new_row(self):
        user = _login_with(self, "view_record", "add_attachment")

        response = self._upload()

        attachment = self.record.attachments.get()
        self.assertEqual((attachment.title, attachment.user), ("Housing damage", user))
        self.assertNotContains(response, "<html")  # the card only
        self.assertNotContains(response, 'type="file"')  # the form is gone again
        self.assertContains(response, f'<img src="{attachment.file.url}"')  # the preview
        self.assertContains(response, str(user))  # who saved it

    def test_without_add_attachment_there_is_no_upload(self):
        _login_with(self, "view_record")

        self.assertNotContains(self.client.get(self.record_url), self.card_url)
        self.assertEqual(self._upload().status_code, 403)
        self.assertFalse(Attachment.objects.exists())
