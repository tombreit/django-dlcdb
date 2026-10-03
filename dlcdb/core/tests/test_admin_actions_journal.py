# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Custom admin actions in the journal, next to their admin history lines."""

import datetime
from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory
from django.urls import reverse

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Device, InRoomRecord, LicenceRecord, Room
from dlcdb.journal.models import JournalEntry

pytestmark = pytest.mark.usefixtures("plain_static")


@pytest.fixture
def admin_user(join_tenant):
    return join_tenant(
        CustomUser.objects.create_superuser(email="admin@example.com", password="secret", username="admin")
    )


@pytest.mark.django_db
def test_deactivating_and_activating_a_room(client, admin_user):
    client.force_login(admin_user)
    room = Room.objects.create(number="R-1")

    client.get(reverse("admin:core_room_deactivate", args=[room.pk]))
    client.get(reverse("admin:core_room_activate", args=[room.pk]))

    deactivated, activated = JournalEntry.objects.order_by("pk")
    assert (deactivated.source, deactivated.event) == ("core.admin", "deactivated")
    assert deactivated.summary == f"Deactivated room: {room}"
    assert deactivated.user == admin_user
    assert deactivated.content_object == room
    assert deactivated.tenant is None
    assert activated.event == "activated"
    # The admin history line stays.
    assert LogEntry.objects.filter(change_message="Deactivated", object_id=str(room.pk)).exists()


@pytest.mark.django_db
def test_deactivating_a_device_carries_its_tenant(client, admin_user, tenant):
    client.force_login(admin_user)
    device = Device.objects.create(edv_id="DEV-1", tenant=tenant)

    client.get(reverse("admin:core_device_deactivate", args=[device.pk]))

    entry = JournalEntry.objects.get()
    assert entry.event == "deactivated"
    assert entry.tenant == tenant


@pytest.mark.django_db
def test_device_note_change_on_a_licence_record(admin_user, tenant):
    device = Device.objects.create(
        edv_id="LIC-1",
        tenant=tenant,
        is_licence=True,
        note="old note",
        contract_start_date=datetime.date(2020, 1, 1),
        contract_expiration_date=datetime.date(2099, 1, 1),
    )
    InRoomRecord.objects.create(device=device, room=Room.objects.create(number="A1.23"))
    record = LicenceRecord.objects.get(device=device)
    request = RequestFactory().post("/")
    request.user = admin_user
    request._messages = SimpleNamespace(add=lambda *args, **kwargs: None)

    admin.site._registry[LicenceRecord].save_model(
        request, record, SimpleNamespace(cleaned_data={"device_note": "new note"}), change=True
    )

    entry = JournalEntry.objects.get()
    assert (entry.source, entry.event, entry.summary) == ("core.admin", "device_note_changed", "Device note changed")
    assert entry.body == "Device note changed. Old value: `old note` New value: `new note`"
    assert entry.content_object == device
    assert entry.tenant == tenant
    assert entry.user == admin_user


@pytest.mark.django_db
def test_deactivating_users(client, make_user):
    anna = CustomUser.objects.create_user(email="anna@example.com", username="anna")
    actor = make_user("accounts.view_customuser", "accounts.change_customuser", is_staff=True)
    client.force_login(actor)

    client.post(
        reverse("admin:accounts_customuser_changelist"), {"action": "deactivate", "_selected_action": [anna.pk]}
    )

    entry = JournalEntry.objects.get()
    assert (entry.source, entry.event) == ("accounts.admin", "deactivated")
    assert entry.summary == "Deactivated user: anna@example.com"
    assert entry.user == actor
    assert entry.content_object == anna


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


@pytest.mark.django_db(transaction=True)
def test_copy_migration_journals_the_custom_admin_actions():
    old_apps = _migrate(
        [
            ("core", "0077_alter_device_tenant_protect"),
            ("journal", "0001_initial"),
            ("accounts", "0003_alter_customuser_email"),
        ]
    )
    ContentType = old_apps.get_model("contenttypes", "ContentType")
    OldLogEntry = old_apps.get_model("admin", "LogEntry")
    Tenant = old_apps.get_model("tenants", "Tenant")
    OldDevice = old_apps.get_model("core", "Device")
    OldUser = old_apps.get_model("accounts", "CustomUser")

    actor = OldUser.objects.create(email="actor@example.com", username="actor")
    tenant = Tenant.objects.create(name="MigTenant")
    device = OldDevice.objects.create(edv_id="MIG-1", tenant=tenant, username="")
    device_type = ContentType.objects.get_or_create(app_label="core", model="device")[0]
    room_type = ContentType.objects.get_or_create(app_label="core", model="room")[0]
    user_type = ContentType.objects.get_or_create(app_label="accounts", model="customuser")[0]

    def history(content_type, object_id, object_repr, message):
        return OldLogEntry.objects.create(
            user=actor,
            content_type=content_type,
            object_id=str(object_id),
            object_repr=object_repr,
            action_flag=2,
            change_message=message,
        )

    note = history(device_type, device.pk, "MIG-1", "Device note changed. Old value: `a` New value: `b`")
    deactivated = history(device_type, device.pk, "MIG-1", "Deactivated")
    activated = history(room_type, 7, "R-7", "Activated")
    user_off = history(user_type, 9, "gone@example.com", "Deactivated.")
    history(room_type, 7, "R-7", '[{"changed": {"fields": ["Note"]}}]')  # an ordinary admin change

    new_apps = _migrate([("core", "0078_copy_admin_actions_to_journal")])
    NewJournalEntry = new_apps.get_model("journal", "JournalEntry")

    entries = {(entry.event, entry.object_id): entry for entry in NewJournalEntry.objects.all()}
    assert len(entries) == 4
    by_action = {
        action.pk: entries[(event, int(action.object_id))]
        for action, event in [
            (note, "device_note_changed"),
            (deactivated, "deactivated"),
            (activated, "activated"),
            (user_off, "deactivated"),
        ]
    }
    assert (by_action[note.pk].event, by_action[note.pk].body) == ("device_note_changed", note.change_message)
    assert by_action[note.pk].tenant_id == tenant.pk
    assert (by_action[deactivated.pk].event, by_action[deactivated.pk].summary) == (
        "deactivated",
        "Deactivated device: MIG-1",
    )
    assert by_action[activated.pk].summary == "Activated room: R-7"
    assert by_action[activated.pk].tenant_id is None
    assert (by_action[user_off.pk].source, by_action[user_off.pk].summary) == (
        "accounts.admin",
        "Deactivated user: gone@example.com",
    )
    assert all(entry.username == "actor@example.com" for entry in entries.values())
    assert by_action[note.pk].timestamp == note.action_time

    # Leave the schema at head so the test DB stays consistent for other tests.
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
