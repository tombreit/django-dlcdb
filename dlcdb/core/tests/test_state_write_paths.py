# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Characterization tests for the state-changing paths that bypass the proxy layer.

Several places move a device between states without going through a proxy
model's ``save()``:

* ``Inventory.inventorize_uuids_for_room`` rewrites ``record_type`` **in place**
  on a cloned record (``core/models/inventory.py``)
* ``dataexchange/remover.py`` writes a plain ``Record`` row via ``get_or_create``
* ``core/admin/device_admin.py::restore_removed_to_lost`` moves REMOVED -> LOST,
  a transition ``STATE_TRANSITIONS`` does not contain
* ``dataexchange/records.py::create_record`` builds records directly for imports

They are pinned here by **outcome only** -- which state the device ends up in,
and which fields were cleaned up -- never by mechanism. A consolidated FSM is
expected to change *how* these work (appending records instead of mutating them)
while keeping the resulting state identical, which keeps these tests green.
"""

import datetime
import json
from io import BytesIO

import pytest
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from dlcdb.core.models import (
    Device,
    InRoomRecord,
    Inventory,
    LentRecord,
    LostRecord,
    Person,
    Record,
    RemovedRecord,
    Room,
)
from dlcdb.core.models.record import SCRAPPED
from dlcdb.dataexchange.records import create_record
from dlcdb.dataexchange.remover import set_removed_record


@pytest.fixture
def inventory_user(db):
    return get_user_model().objects.create_superuser(email="inventory@example.com", password="secret")


@pytest.fixture
def inventory_rooms(db):
    """The two singleton rooms the inventory flow depends on, plus a target room."""
    return {
        "target": Room.objects.create(number="INV-TARGET"),
        "external": Room.objects.create(number="INV-EXTERN", is_external=True),
    }


def _inventorize(device, state, room, user):
    Inventory.inventorize_uuids_for_room(
        uuids=json.dumps({str(device.uuid): state}),
        room_pk=room.pk,
        user=user,
    )
    device.refresh_from_db()
    return device.active_record


# --- Inventory: "found" -------------------------------------------------


@pytest.mark.django_db
def test_inventory_found_relocates_a_located_device(inventory_1, inventory_rooms, inventory_user):
    device = Device.objects.create(edv_id="EDV-INV-1")
    other_room = Room.objects.create(number="ELSEWHERE")
    InRoomRecord.objects.create(device=device, room=other_room)

    record = _inventorize(device, "dev_state_found", inventory_rooms["target"], inventory_user)

    assert record.record_type == Record.INROOM
    assert record.room == inventory_rooms["target"]
    assert record.inventory == inventory_1


@pytest.mark.django_db
def test_inventory_found_recovers_a_lost_device(inventory_1, inventory_rooms, inventory_user):
    """Finding a device during stocktaking brings it back from LOST."""
    device = Device.objects.create(edv_id="EDV-INV-LOST")
    LostRecord.objects.create(device=device)

    record = _inventorize(device, "dev_state_found", inventory_rooms["target"], inventory_user)

    assert record.record_type == Record.INROOM
    assert record.room == inventory_rooms["target"]


@pytest.mark.django_db
def test_inventory_found_recovers_a_removed_device_and_clears_removal_fields(
    inventory_1, inventory_rooms, inventory_user
):
    """
    REMOVED -> INROOM. Note ``STATE_TRANSITIONS`` declares REMOVED terminal
    (``REMOVED: [None]``), so this transition is performed by production code
    but absent from the table -- one of the reasons the table must be corrected
    rather than merely enforced.
    """
    device = Device.objects.create(edv_id="EDV-INV-RM")
    RemovedRecord.objects.create(
        device=device,
        disposition_state=SCRAPPED,
        removed_info="scrapped in 2024",
    )

    record = _inventorize(device, "dev_state_found", inventory_rooms["target"], inventory_user)

    assert record.record_type == Record.INROOM
    assert record.room == inventory_rooms["target"]
    # The removal-specific fields must not leak into the new state. The recovered
    # device now gets a fresh InRoomRecord (rather than a cloned-and-blanked
    # REMOVED record), so these are simply unset -- None or empty, not populated.
    assert not record.disposition_state
    assert not record.removed_info
    assert record.removed_date is None


# --- Inventory: "not found" ---------------------------------------------


@pytest.mark.django_db
def test_inventory_not_found_marks_a_located_device_as_lost(inventory_1, inventory_rooms, inventory_user):
    device = Device.objects.create(edv_id="EDV-INV-NF")
    InRoomRecord.objects.create(device=device, room=inventory_rooms["target"])

    record = _inventorize(device, "dev_state_notfound", inventory_rooms["target"], inventory_user)

    assert record.record_type == Record.LOST
    assert record.inventory == inventory_1


@pytest.mark.django_db
def test_inventory_not_found_preserves_a_lending(inventory_1, inventory_rooms, inventory_user):
    """
    A lent device missing from its room is not "lost" -- it is with its
    borrower. The lending is kept and the device moves to the external room.
    """
    device = Device.objects.create(edv_id="EDV-INV-LENT", is_lentable=True)
    person = Person.objects.create(first_name="Max", last_name="Mustermann")
    LentRecord.objects.create(
        device=device,
        person=person,
        room=inventory_rooms["target"],
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )

    record = _inventorize(device, "dev_state_notfound", inventory_rooms["target"], inventory_user)

    assert record.record_type == Record.LENT
    assert record.person == person
    assert record.room == inventory_rooms["external"]


# --- Admin: restore from REMOVED ----------------------------------------


def _run_admin_action(action_name, user, queryset):
    """Invoke a ModelAdmin action the way the changelist does."""
    request = RequestFactory().post("/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)

    model_admin = admin_site._registry[Device]
    getattr(model_admin, action_name)(request, queryset)


@pytest.mark.django_db
def test_restore_removed_to_lost_moves_the_device_out_of_removed():
    """
    ``device_admin.restore_removed_to_lost`` performs REMOVED -> LOST, another
    transition missing from ``STATE_TRANSITIONS``. Pinned here so a corrected
    table keeps it legal.
    """
    superuser = get_user_model().objects.create_superuser(email="root@example.com", password="secret")
    device = Device.objects.create(edv_id="EDV-RESTORE")
    RemovedRecord.objects.create(device=device)
    device.refresh_from_db()
    assert device.active_record.record_type == Record.REMOVED

    _run_admin_action("restore_removed_to_lost", superuser, Device.objects.filter(pk=device.pk))

    device.refresh_from_db()
    assert device.active_record.record_type == Record.LOST
    # The removal stays in the history.
    assert device.record_set.filter(record_type=Record.REMOVED).exists()


@pytest.mark.django_db
def test_restore_removed_to_lost_is_superuser_only():
    staff = get_user_model().objects.create_user(email="staff@example.com", password="secret", is_staff=True)
    device = Device.objects.create(edv_id="EDV-RESTORE-DENIED")
    RemovedRecord.objects.create(device=device)

    _run_admin_action("restore_removed_to_lost", staff, Device.objects.filter(pk=device.pk))

    device.refresh_from_db()
    assert device.active_record.record_type == Record.REMOVED


@pytest.mark.django_db
def test_restore_removed_to_lost_ignores_devices_in_other_states(room):
    """The action must only act on REMOVED devices, never on live ones."""
    superuser = get_user_model().objects.create_superuser(email="root2@example.com", password="secret")
    device = Device.objects.create(edv_id="EDV-RESTORE-INROOM")
    InRoomRecord.objects.create(device=device, room=room)

    _run_admin_action("restore_removed_to_lost", superuser, Device.objects.filter(pk=device.pk))

    device.refresh_from_db()
    assert device.active_record.record_type == Record.INROOM


# --- Bulk decommissioning (dataexchange.remover) -------------------------


def _remover_csv(rows):
    header = "SAP_ID,EDV_ID,NOTE,DISPOSITION_STATE,REMOVED_INFO,REMOVED_DATE,USERNAME"
    body = "\n".join(rows)
    return BytesIO(f"{header}\n{body}\n".encode())


@pytest.mark.django_db
def test_remover_marks_a_device_as_removed(room):
    user = get_user_model().objects.create_user(username="remover", email="remover@example.com", password="secret")
    device = Device.objects.create(edv_id="EDV-REMOVE", sap_id="900-1")
    InRoomRecord.objects.create(device=device, room=room)

    set_removed_record(
        _remover_csv([f"900-1,EDV-REMOVE,bulk decommission,{SCRAPPED},recycled,,remover"]),
        username=user.username,
        write=True,
    )

    device.refresh_from_db()
    assert device.active_record.record_type == Record.REMOVED
    assert device.active_record.disposition_state == SCRAPPED


@pytest.mark.django_db
def test_remover_refuses_to_remove_an_already_removed_device():
    user = get_user_model().objects.create_user(username="remover", email="remover@example.com", password="secret")
    device = Device.objects.create(edv_id="EDV-REMOVE-2", sap_id="900-2")
    RemovedRecord.objects.create(device=device)

    with pytest.raises(ValidationError):
        set_removed_record(
            _remover_csv([f"900-2,EDV-REMOVE-2,again,{SCRAPPED},,,remover"]),
            username=user.username,
            write=True,
        )


@pytest.mark.django_db
def test_remover_dry_run_changes_nothing(room):
    user = get_user_model().objects.create_user(username="remover", email="remover@example.com", password="secret")
    device = Device.objects.create(edv_id="EDV-REMOVE-3", sap_id="900-3")
    InRoomRecord.objects.create(device=device, room=room)

    set_removed_record(
        _remover_csv([f"900-3,EDV-REMOVE-3,dry run,{SCRAPPED},,,remover"]),
        username=user.username,
        write=False,
    )

    device.refresh_from_db()
    assert device.active_record.record_type == Record.INROOM


# --- Import: create_record ----------------------------------------------


@pytest.mark.django_db
def test_import_defaults_to_inroom_when_only_a_room_is_given():
    device = Device.objects.create(edv_id="EDV-IMP-1")
    room = Room.objects.create(number="IMP-1")

    records = create_record(
        device=device,
        record_type="",
        record_note="",
        room=room.number,
        username="importer",
        removed_date=None,
    )

    # create_record() returns *unsaved* proxies; record_type is stamped by save().
    assert [type(r) for r in records] == [InRoomRecord]


@pytest.mark.django_db
def test_import_of_a_completed_loan_yields_lent_then_inroom():
    """
    A single CSV row can describe a whole finished lending. The import replays
    it as two records, in order, so the device ends up available again.
    """
    device = Device.objects.create(edv_id="EDV-IMP-2", is_lentable=True)
    room = Room.objects.create(number="IMP-2")

    records = create_record(
        device=device,
        record_type=Record.LENT,
        record_note="",
        room=room.number,
        username="importer",
        removed_date=None,
        lender_first_name="Max",
        lender_last_name="Mustermann",
        lender_email="max@example.com",
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2026, 2, 1),
        lent_end_date=datetime.date(2026, 1, 20),
    )

    assert [type(r) for r in records] == [LentRecord, InRoomRecord]

    for record in records:
        record.save()

    device.refresh_from_db()
    assert device.active_record.record_type == Record.INROOM
    assert device.record_set.count() == 2


@pytest.mark.django_db
def test_import_of_an_open_loan_yields_only_a_lent_record():
    device = Device.objects.create(edv_id="EDV-IMP-3", is_lentable=True)
    room = Room.objects.create(number="IMP-3")

    records = create_record(
        device=device,
        record_type=Record.LENT,
        record_note="",
        room=room.number,
        username="importer",
        removed_date=None,
        lender_first_name="Max",
        lender_last_name="Mustermann",
        lender_email="max@example.com",
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2099, 1, 1),
    )

    assert [type(r) for r in records] == [LentRecord]
