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

from django.test import TestCase

from dlcdb.core.models import InRoomRecord, LostRecord, Record, Room
from dlcdb.core.tests.basetest import BaseTest

from ..filters import RecordFilter


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
