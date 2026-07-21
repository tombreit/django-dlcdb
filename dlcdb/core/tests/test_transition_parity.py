# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for the *duplicated* transition logic.

The lend/return state machine currently exists three times:

* ``dlcdb/core/admin/lentrecord_admin.py::LentRecordAdmin.save_model``
* ``dlcdb/lending/views.py::_apply_state_machine`` (whose docstring says it
  "replicates" the admin one)
* ``dlcdb/dataexchange/records.py::create_record`` (the CSV import variant)

and the rule "a lost device cannot be lent" exists three times on top of that.

These tests assert the copies *agree*. They are the safety net for merging them:
if a consolidated FSM changes behaviour, the two paths stop matching and these
fail. They compare outcomes only, so the merge itself is invisible to them.
"""

import datetime

from unittest import expectedFailure

from django.contrib.auth import get_user_model
from django.forms import modelform_factory
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.forms.lentrecordadmin_form import LentRecordAdminForm
from dlcdb.core.forms.removedrecord_form import RemovedRecordAdminForm
from dlcdb.core.models import Device, InRoomRecord, LentRecord, LostRecord, Person, Record, RemovedRecord, Room
from dlcdb.core.models.record import SCRAPPED
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.core.utils.relocate import relocate_device
from dlcdb.lending.forms import LentingForm

# Plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

LEND_START = "2026-06-23"
LEND_DESIRED_END = "2026-07-23"
RETURN_DATE = "2026-06-30"


def snapshot(device):
    """
    The externally observable state of a device, for comparing two code paths
    that are supposed to do the same thing.
    """
    device.refresh_from_db()
    record = device.active_record
    return {
        "record_type": record.record_type,
        "person_id": record.person_id,
        "room_number": record.room.number if record.room else None,
        "lent_start_date": record.lent_start_date,
        "lent_desired_end_date": record.lent_desired_end_date,
        "lent_end_date": record.lent_end_date,
        "chain_length": device.record_set.count(),
    }


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LendReturnParityTests(BaseTest):
    """The admin and the frontend must produce identical state changes."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room = Room.objects.create(number="A1.23", nickname="Theke")
        cls.auto_return_room = Room.objects.create(number="RETURN", is_auto_return_room=True)
        cls.external_room = Room.objects.create(number="EXTERN", is_external=True)
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com")

    def setUp(self):
        self.client.force_login(self.user)

    def _available_device(self, edv_id, sap_id):
        device = self._create_device(edv_id=edv_id, sap_id=sap_id)
        device.is_lentable = True
        device.save()
        record = InRoomRecord.objects.create(device=device, room=self.room)
        return device, record

    def _lent_device(self, edv_id, sap_id):
        device = self._create_device(edv_id=edv_id, sap_id=sap_id)
        device.is_lentable = True
        device.save()
        record = LentRecord.objects.create(
            device=device,
            person=self.person,
            room=self.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )
        return device, record

    def _payload(self, **overrides):
        payload = {
            "person": self.person.id,
            "room": self.room.id,
            "lent_start_date": LEND_START,
            "lent_desired_end_date": LEND_DESIRED_END,
            "lent_accessories": "",
            "lent_reason": "",
            "lent_note": "",
        }
        payload.update(overrides)
        return payload

    def _post_admin(self, record, **overrides):
        payload = self._payload(**overrides)
        payload.pop("lent_reason", None)  # not part of the admin fieldsets
        payload["_save"] = ""
        return self.client.post(reverse("admin:core_lentrecord_change", args=[record.pk]), payload)

    def _post_frontend(self, record, **overrides):
        return self.client.post(reverse("lending:detail", args=[record.pk]), self._payload(**overrides))

    # --- lend ------------------------------------------------------------

    def test_lend_via_admin_and_via_frontend_agree(self):
        admin_device, admin_record = self._available_device("EDV-ADM-LEND", "1-1")
        front_device, front_record = self._available_device("EDV-FE-LEND", "2-2")

        self._post_admin(admin_record)
        self._post_frontend(front_record)

        admin_state = snapshot(admin_device)
        self.assertEqual(admin_state["record_type"], Record.LENT)
        self.assertEqual(admin_state["person_id"], self.person.id)
        self.assertEqual(admin_state["lent_end_date"], None)
        # Lending appends exactly one record; the InRoom record is kept as history.
        self.assertEqual(admin_state["chain_length"], 2)

        self.assertEqual(admin_state, snapshot(front_device))

    def test_lend_closes_the_previous_inroom_record_on_both_paths(self):
        admin_device, admin_record = self._available_device("EDV-ADM-CLOSE", "3-3")
        front_device, front_record = self._available_device("EDV-FE-CLOSE", "4-4")

        self._post_admin(admin_record)
        self._post_frontend(front_record)

        for record in (admin_record, front_record):
            record.refresh_from_db()
            self.assertFalse(record.is_active)
            self.assertIsNotNone(record.effective_until)

    # --- return ----------------------------------------------------------

    def test_return_via_admin_and_via_frontend_agree(self):
        admin_device, admin_record = self._lent_device("EDV-ADM-RET", "5-5")
        front_device, front_record = self._lent_device("EDV-FE-RET", "6-6")

        self._post_admin(admin_record, lent_end_date=RETURN_DATE)
        self._post_frontend(front_record, lent_end_date=RETURN_DATE)

        admin_state = snapshot(admin_device)
        # Returning ends the lending and parks the device in the auto-return room.
        self.assertEqual(admin_state["record_type"], Record.INROOM)
        self.assertEqual(admin_state["room_number"], self.auto_return_room.number)
        self.assertEqual(admin_state["chain_length"], 2)

        self.assertEqual(admin_state, snapshot(front_device))

    def test_return_stamps_the_end_date_on_the_lending_on_both_paths(self):
        admin_device, admin_record = self._lent_device("EDV-ADM-STAMP", "7-7")
        front_device, front_record = self._lent_device("EDV-FE-STAMP", "8-8")

        self._post_admin(admin_record, lent_end_date=RETURN_DATE)
        self._post_frontend(front_record, lent_end_date=RETURN_DATE)

        expected = datetime.date.fromisoformat(RETURN_DATE)
        for record in (admin_record, front_record):
            record.refresh_from_db()
            self.assertEqual(record.record_type, Record.LENT)
            self.assertEqual(record.lent_end_date, expected)

    # --- edit ------------------------------------------------------------

    def test_editing_a_lending_appends_nothing_on_both_paths(self):
        admin_device, admin_record = self._lent_device("EDV-ADM-EDIT", "9-9")
        front_device, front_record = self._lent_device("EDV-FE-EDIT", "10-10")

        self._post_admin(admin_record, lent_note="Charger included")
        self._post_frontend(front_record, lent_note="Charger included")

        admin_state = snapshot(admin_device)
        self.assertEqual(admin_state["record_type"], Record.LENT)
        self.assertEqual(admin_state["chain_length"], 1)
        self.assertEqual(admin_state, snapshot(front_device))


class LostDeviceCannotBeLentTests(BaseTest):
    """The same rule, asserted against each of its three implementations."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room = Room.objects.create(number="A1.23")
        cls.auto_return_room = Room.objects.create(number="RETURN", is_auto_return_room=True)
        cls.external_room = Room.objects.create(number="EXTERN", is_external=True)
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann")

    def _form_data(self):
        return {
            "person": self.person.id,
            "room": self.room.id,
            "lent_start_date": LEND_START,
            "lent_desired_end_date": LEND_DESIRED_END,
        }

    @staticmethod
    def _admin_form(**kwargs):
        """
        ``LentRecordAdminForm`` declares ``exclude = []``; the admin narrows it
        to the editable fields of ``LentRecordAdmin.fieldsets``. Mirror that,
        otherwise ``device``/``record_type`` come out spuriously required.
        """
        form_class = modelform_factory(
            LentRecord,
            form=LentRecordAdminForm,
            fields=(
                "person",
                "room",
                "lent_start_date",
                "lent_desired_end_date",
                "sync_lent_end_date",
                "lent_end_date",
                "lent_accessories",
                "lent_note",
            ),
        )
        return form_class(**kwargs)

    def _lost_lentable_record(self, edv_id, sap_id):
        """
        A lost device that is otherwise perfectly lendable, resolved through the
        LentRecord proxy the way both forms receive it in production. Everything
        except the "lost" state is valid, so a rejection can only come from the
        guard under test.
        """
        device = self._create_device(edv_id=edv_id, sap_id=sap_id)
        device.is_lentable = True
        device.save()
        lost = LostRecord.objects.create(device=device)
        return LentRecord.objects.get(pk=lost.pk)

    def test_admin_form_rejects_lending_a_lost_device(self):
        instance = self._lost_lentable_record("EDV-LOST-ADM", "20-20")
        form = self._admin_form(data=self._form_data(), instance=instance)
        form.record_type = Record.LOST

        self.assertFalse(form.is_valid())
        self.assertIn("not locatable", str(form.errors))

    def test_lending_form_rejects_lending_a_lost_device(self):
        instance = self._lost_lentable_record("EDV-LOST-FE", "21-21")
        form = LentingForm(data=self._form_data(), instance=instance, record_type=Record.LOST)

        self.assertFalse(form.is_valid())
        self.assertIn("not locatable", str(form.errors))

    def test_both_forms_accept_an_available_device(self):
        """The guards must not reject a normal lending -- otherwise the tests above prove nothing."""
        device = self._create_device(edv_id="EDV-OK", sap_id="22-22")
        device.is_lentable = True
        device.save()
        inroom = InRoomRecord.objects.create(device=device, room=self.room)
        instance = LentRecord.objects.get(pk=inroom.pk)

        admin_form = self._admin_form(data=self._form_data(), instance=instance)
        admin_form.record_type = Record.INROOM
        self.assertTrue(admin_form.is_valid(), admin_form.errors)

        lending_form = LentingForm(data=self._form_data(), instance=instance, record_type=Record.INROOM)
        self.assertTrue(lending_form.is_valid(), lending_form.errors)

    def test_lending_view_rejects_lending_a_lost_device(self):
        device = self._create_device(edv_id="EDV-LOST-LEND", sap_id="11-11")
        device.is_lentable = True
        device.save()
        record = LostRecord.objects.create(device=device)

        self.client.force_login(self.user)
        response = self.client.post(reverse("lending:detail", args=[record.pk]), self._form_data())

        # The view refuses to open a lend flow on a non-INROOM record.
        self.assertIn(response.status_code, (302, 404))
        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.LOST)


class RemoveTwiceTests(BaseTest):
    """
    ``RemovedRecordAdminForm`` carries no ``Meta.model``; the admin supplies it.
    Build it the same way, mirroring ``RemovedRecordAdmin.fields``.
    """

    @staticmethod
    def _form(**data):
        form_class = modelform_factory(
            RemovedRecord,
            form=RemovedRecordAdminForm,
            fields=("device", "disposition_state", "removed_info"),
        )
        return form_class(data=data)

    def test_removed_device_cannot_be_removed_again(self):
        device = self._create_device(edv_id="EDV-RM", sap_id="12-12")
        RemovedRecord.objects.create(device=device)
        device.refresh_from_db()

        form = self._form(device=device.pk, disposition_state=SCRAPPED)

        self.assertFalse(form.is_valid())
        self.assertIn("can not be removed again", str(form.errors))

    def test_a_located_device_can_be_removed(self):
        room = Room.objects.create(number="B2.01")
        device = self._create_device(edv_id="EDV-RM-OK", sap_id="13-13")
        InRoomRecord.objects.create(device=device, room=room)
        device.refresh_from_db()

        form = self._form(device=device.pk, disposition_state=SCRAPPED)

        self.assertTrue(form.is_valid(), form.errors)

    @expectedFailure
    def test_removing_a_device_without_any_record_is_rejected_gracefully(self):
        """
        Known defect: ``RemovedRecordAdminForm.clean()`` reads
        ``device.active_record.record_type`` unguarded, so a device that has no
        record yet raises AttributeError instead of failing validation. A
        consolidated FSM guard (which treats "no active record" as a state)
        fixes this, at which point this test flips to green.
        """
        device = self._create_device(edv_id="EDV-RM-NONE", sap_id="17-17")
        self.assertIsNone(device.active_record)

        form = self._form(device=device.pk, disposition_state=SCRAPPED)

        self.assertFalse(form.is_valid())


class RelocateBranchTests(BaseTest):
    """
    ``relocate_device`` is the one transition that has already been consolidated
    (``core/utils/relocate.py``) and is the precedent a central FSM should follow.
    ``assets/tests/test_relocate.py`` covers the HTTP layer; these cover the
    branches it does not.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="mover@example.com", password="secret")
        cls.room_a = Room.objects.create(number="A1.01")
        cls.room_b = Room.objects.create(number="B2.02")
        cls.auto_return_room = Room.objects.create(number="RETURN", is_auto_return_room=True)
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann")

    def test_relocating_a_lent_device_moves_it_without_ending_the_lending(self):
        device = self._create_device(edv_id="EDV-MOVE-LENT", sap_id="14-14")
        device.is_lentable = True
        device.save()
        record = LentRecord.objects.create(
            device=device,
            person=self.person,
            room=self.room_a,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        relocate_device(device, self.room_b, self.user)

        device.refresh_from_db()
        record.refresh_from_db()
        # Still lent, to the same person -- only the room changed.
        self.assertEqual(device.active_record.record_type, Record.LENT)
        self.assertEqual(device.active_record.pk, record.pk)
        self.assertEqual(record.room, self.room_b)
        self.assertEqual(record.person, self.person)

    def test_relocating_to_the_same_room_is_a_no_op(self):
        device = self._create_device(edv_id="EDV-MOVE-SAME", sap_id="15-15")
        InRoomRecord.objects.create(device=device, room=self.room_a)
        device.refresh_from_db()
        before = device.record_set.count()

        relocate_device(device, self.room_a, self.user)

        device.refresh_from_db()
        self.assertEqual(device.record_set.count(), before)
        self.assertEqual(device.active_record.room, self.room_a)

    def test_relocating_a_removed_device_is_refused(self):
        device = self._create_device(edv_id="EDV-MOVE-RM", sap_id="16-16")
        RemovedRecord.objects.create(device=device)
        device.refresh_from_db()
        before = device.record_set.count()

        relocate_device(device, self.room_b, self.user)

        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.REMOVED)
        self.assertEqual(device.record_set.count(), before)

    def test_relocating_a_device_without_a_record_locates_it(self):
        device = Device.objects.create(edv_id="EDV-MOVE-NEW")

        relocate_device(device, self.room_b, self.user)

        device.refresh_from_db()
        self.assertEqual(device.active_record.record_type, Record.INROOM)
        self.assertEqual(device.active_record.room, self.room_b)
