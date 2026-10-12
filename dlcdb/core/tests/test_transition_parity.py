# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Parity tests for the two places a lending is entered:

* ``dlcdb/core/admin/lentrecord_admin.py::LentRecordAdmin.save_model``
* ``dlcdb/lending/views.py::_save_lending``

Both save through ``LentRecord.apply_lending`` and show
``LentRecord.contract_warnings``. These tests assert that the two paths produce the
same record chain, stamp the same editor, show the same warnings and both refuse to
lend a lost device. They compare outcomes only.

The admin remove form's guards and the relocate branches are pinned here too.
"""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.messages import WARNING, get_messages
from django.forms import modelform_factory
from django.test import override_settings
from django.urls import reverse

from dlcdb.core import lifecycle
from dlcdb.core.forms.removedrecord_form import RemovedRecordAdminForm
from dlcdb.core.models import (
    Device,
    InRoomRecord,
    LentRecord,
    LostRecord,
    OrderedRecord,
    Person,
    Record,
    RemovedRecord,
    Room,
)
from dlcdb.core.models.record import SCRAPPED
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.core.utils.relocate import relocate_device
from dlcdb.lending.models import LendingProfile

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
        cls()._join_default_tenant(cls.user)
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
        record = establish_state(
            LentRecord,
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

    def _post_frontend_return(self, record, **overrides):
        """
        The frontend return screen (``?flow=return``) posts only the return
        fields; the admin submits the whole change form for the same transition.
        """
        payload = {"lent_end_date": RETURN_DATE, "lent_note": ""}
        payload.update(overrides)
        return self.client.post(f"{reverse('lending:detail', args=[record.pk])}?flow=return", payload)

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
        _admin_device, admin_record = self._available_device("EDV-ADM-CLOSE", "3-3")
        _front_device, front_record = self._available_device("EDV-FE-CLOSE", "4-4")

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
        self._post_frontend_return(front_record)

        admin_state = snapshot(admin_device)
        # Returning ends the lending and parks the device in the auto-return room.
        self.assertEqual(admin_state["record_type"], Record.INROOM)
        self.assertEqual(admin_state["room_number"], self.auto_return_room.number)
        self.assertEqual(admin_state["chain_length"], 2)

        self.assertEqual(admin_state, snapshot(front_device))

    def test_return_stamps_the_end_date_on_the_lending_on_both_paths(self):
        _admin_device, admin_record = self._lent_device("EDV-ADM-STAMP", "7-7")
        _front_device, front_record = self._lent_device("EDV-FE-STAMP", "8-8")

        self._post_admin(admin_record, lent_end_date=RETURN_DATE)
        self._post_frontend_return(front_record)

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

    def test_editing_a_lending_stamps_the_editor_on_both_paths(self):
        """The test lendings have no editor yet; saving an edit records the helpdesk user."""
        _admin_device, admin_record = self._lent_device("EDV-ADM-EDITOR", "11-11")
        _front_device, front_record = self._lent_device("EDV-FE-EDITOR", "12-12")

        self._post_admin(admin_record, lent_note="Charger included")
        self._post_frontend(front_record, lent_note="Charger included")

        for record in (admin_record, front_record):
            record.refresh_from_db()
            self.assertEqual(record.user, self.user)
            self.assertEqual(record.username, "helpdesk@example.com")

    # --- lend, edit and return in a row ------------------------------------

    @staticmethod
    def _chain(device):
        """The device's records, oldest first, with what the lending screens write."""
        return [
            (record.record_type, record.room.number, record.lent_note, record.lent_end_date, record.username)
            for record in device.record_set.order_by("pk")
        ]

    def test_lend_edit_and_return_leave_the_same_record_chain_on_both_paths(self):
        admin_device, admin_record = self._available_device("EDV-ADM-CHAIN", "13-13")
        front_device, front_record = self._available_device("EDV-FE-CHAIN", "14-14")

        self._post_admin(admin_record)
        admin_lending = LentRecord.objects.get(device=admin_device, record_type=Record.LENT)
        self._post_admin(admin_lending, lent_note="Charger included")
        self._post_admin(admin_lending, lent_note="Charger included", lent_end_date=RETURN_DATE)

        self._post_frontend(front_record)
        front_lending = LentRecord.objects.get(device=front_device, record_type=Record.LENT)
        self._post_frontend(front_lending, lent_note="Charger included")
        self._post_frontend_return(front_lending, lent_note="Charger included")

        returned = datetime.date.fromisoformat(RETURN_DATE)
        self.assertEqual(
            self._chain(admin_device),
            [
                (Record.INROOM, self.room.number, "", None, ""),
                (Record.LENT, self.room.number, "Charger included", returned, "helpdesk@example.com"),
                (Record.INROOM, self.auto_return_room.number, "", None, "helpdesk@example.com"),
            ],
        )
        self.assertEqual(self._chain(admin_device), self._chain(front_device))

    # --- contract warnings -----------------------------------------------

    def _warnings(self, response):
        """
        The warnings the save added. The client then drops the message cookie, so
        the next save in the same test starts without them.
        """
        warnings = [str(message) for message in get_messages(response.wsgi_request) if message.level == WARNING]
        self.client.cookies.pop("messages", None)
        return warnings

    def test_both_paths_warn_about_a_missing_contract_end_date(self):
        _admin_device, admin_record = self._available_device("EDV-ADM-NO-CONTRACT", "15-15")
        _front_device, front_record = self._available_device("EDV-FE-NO-CONTRACT", "16-16")

        admin_warnings = self._warnings(self._post_admin(admin_record))
        front_warnings = self._warnings(self._post_frontend(front_record))

        self.assertEqual(admin_warnings, ["Warning: No HR contract end date found for Mustermann, Max!"])
        self.assertEqual(admin_warnings, front_warnings)

    def test_both_paths_warn_about_a_contract_ending_before_the_desired_return(self):
        self.person.udb_contract_planned_checkout = datetime.date.fromisoformat(LEND_DESIRED_END) - datetime.timedelta(
            days=1
        )
        self.person.save()
        _admin_device, admin_record = self._available_device("EDV-ADM-SHORT-CONTRACT", "17-17")
        _front_device, front_record = self._available_device("EDV-FE-SHORT-CONTRACT", "18-18")

        admin_warnings = self._warnings(self._post_admin(admin_record))
        front_warnings = self._warnings(self._post_frontend(front_record))

        self.assertEqual(admin_warnings, ["Warning: Contract ends before the desired return date!"])
        self.assertEqual(admin_warnings, front_warnings)


# The lifecycle's refusals (``lifecycle.check``), as the lending screens show them.
LOST_REFUSAL = "“Lend” is not allowed for a device in state “Not locatable”."
ORDERED_REFUSAL = "“Lend” is not allowed for a device in state “Ordered”."


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class LostDeviceCannotBeLentTests(BaseTest):
    """
    The lending screens can act on a lending and on a device that can be lent now;
    the lifecycle decides which (``LentRecord.check_lending``). A lost or an ordered
    device gets the lifecycle's refusal on both screens: no lending, no server error,
    no lending screen.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls()._join_default_tenant(cls.user)
        cls.room = Room.objects.create(number="A1.23")
        cls.auto_return_room = Room.objects.create(number="RETURN", is_auto_return_room=True)
        cls.external_room = Room.objects.create(number="EXTERN", is_external=True)
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann")

    def setUp(self):
        self.client.force_login(self.user)

    def _lentable_device_in(self, proxy_model, edv_id, sap_id, **fields):
        """
        A lentable device whose active record is of ``proxy_model``, resolved through
        the LentRecord proxy the way both screens receive it. Everything except the
        state is fit for lending, so a refusal can only come from the state.
        """
        device = self._create_device(edv_id=edv_id, sap_id=sap_id)
        device.is_lentable = True
        device.save()
        record = establish_state(proxy_model, device=device, **fields)
        return LentRecord.objects.get(pk=record.pk)

    def _refused(self):
        """A lost and an ordered device, each with the refusal the screens show for it."""
        return (
            (self._lentable_device_in(LostRecord, "EDV-LOST", "20-20"), LOST_REFUSAL),
            (self._lentable_device_in(OrderedRecord, "EDV-ORDERED", "21-21"), ORDERED_REFUSAL),
        )

    def _payload(self):
        return {
            "person": self.person.id,
            "room": self.room.id,
            "lent_start_date": LEND_START,
            "lent_desired_end_date": LEND_DESIRED_END,
            "lent_accessories": "",
            "lent_note": "",
        }

    def test_check_lending_passes_an_available_device_and_a_lending(self):
        available = self._lentable_device_in(InRoomRecord, "EDV-AVAILABLE", "22-22", room=self.room)
        lending = self._lentable_device_in(
            LentRecord,
            "EDV-LENT",
            "23-23",
            person=self.person,
            room=self.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        available.check_lending()
        lending.check_lending()

    def test_check_lending_refuses_a_lost_and_an_ordered_device(self):
        for record, refusal in self._refused():
            with self.subTest(record.record_type), self.assertRaisesMessage(lifecycle.IllegalTransition, refusal):
                record.check_lending()

    def test_apply_lending_refuses_a_lost_device_and_writes_nothing(self):
        record = self._lentable_device_in(LostRecord, "EDV-LOST-APPLY", "24-24")
        record.person, record.room = self.person, self.room
        record.lent_start_date = datetime.date.fromisoformat(LEND_START)
        record.lent_desired_end_date = datetime.date.fromisoformat(LEND_DESIRED_END)

        with self.assertRaisesMessage(lifecycle.IllegalTransition, LOST_REFUSAL):
            record.apply_lending(user=self.user)

        self.assertEqual(record.device.record_set.count(), 1)

    def test_the_admin_shows_the_refusal_instead_of_lending(self):
        for record, refusal in self._refused():
            with self.subTest(record.record_type):
                response = self.client.post(
                    reverse("admin:core_lentrecord_change", args=[record.pk]), {**self._payload(), "_save": ""}
                )

                self.assertContains(response, refusal)
                self.assertEqual(record.device.record_set.count(), 1)

    def _assert_refused(self, response, refusal):
        """
        The lending screen sent the user back to the index with the refusal. The
        client then drops the message cookie, so the next request starts without it.
        """
        self.assertRedirects(response, reverse("lending:index"), fetch_redirect_response=False)
        self.assertEqual([str(message) for message in get_messages(response.wsgi_request)], [refusal])
        self.client.cookies.pop("messages", None)

    def test_the_lending_screen_shows_the_refusal_instead_of_opening(self):
        for record, refusal in self._refused():
            url = reverse("lending:detail", args=[record.pk])
            with self.subTest(record.record_type):
                self._assert_refused(self.client.get(url), refusal)
                self._assert_refused(self.client.post(url, self._payload()), refusal)
                self.assertEqual(record.device.record_set.count(), 1)

    def test_only_a_device_that_can_be_lent_gets_a_lending_slip(self):
        available = self._lentable_device_in(InRoomRecord, "EDV-SLIP", "25-25", room=self.room)
        # The device type prints a slip, so a 404 below can only come from the state.
        LendingProfile.objects.create(device_type=available.device.device_type, lent_sheet_template="Slip")

        def print_sheet(record):
            return self.client.post(reverse("lending:print_sheet", args=[record.device.pk]), self._payload())

        self.assertEqual(print_sheet(available).status_code, 200)
        for record, _refusal in self._refused():
            with self.subTest(record.record_type):
                self.assertEqual(print_sheet(record).status_code, 404)


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

    def test_removing_a_device_without_any_record_is_rejected_gracefully(self):
        """
        The admin form refuses a device with no record yet, although the lifecycle
        allows None -> REMOVED for the bulk remover: it has to be localized first.
        """
        device = self._create_device(edv_id="EDV-RM-NONE", sap_id="17-17")
        self.assertIsNone(device.active_record)

        form = self._form(device=device.pk, disposition_state=SCRAPPED)

        self.assertFalse(form.is_valid())


class RelocateBranchTests(BaseTest):
    """
    ``relocate_device`` (``core/utils/relocate.py``) moves a device for the admin
    bulk relocate and the assets Move module. ``assets/tests/test_relocate.py``
    covers the HTTP layer; these cover the branches it does not.
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
        record = establish_state(
            LentRecord,
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
