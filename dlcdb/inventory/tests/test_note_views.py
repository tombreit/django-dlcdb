# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Permission guards for the inventory note endpoints (note button, note
create/edit, note delete). All three are reached over HTMX, so a missing
permission short-circuits with a client refresh instead of a 403 page.
They work on the active inventory's notes only, and an unknown object is a 404.
"""

import uuid

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Inventory, Note


@pytest.fixture
def plain_user(db):
    return CustomUser.objects.create_user(username="plain", email="plain@example.org", password="pw")


@pytest.fixture
def inventorizing_user(db):
    user = CustomUser.objects.create_user(username="inv", email="inv@example.org", password="pw")
    user.user_permissions.add(Permission.objects.get(codename="can_inventorize"))
    return user


@pytest.fixture
def room_note(db, room_1, inventory_1):
    return Note.objects.create(text="a note", room=room_1, inventory=inventory_1)


@pytest.mark.django_db
def test_delete_note_denied_without_permission(client, plain_user, room_note):
    client.force_login(plain_user)
    response = client.post(
        reverse("inventory:note-delete", kwargs={"pk": room_note.pk}), headers={"HX-Request": "true"}
    )

    assert response["HX-Refresh"] == "true"
    assert Note.objects.filter(pk=room_note.pk).exists()


@pytest.mark.django_db
def test_delete_note_allowed_with_permission(client, inventorizing_user, room_note):
    client.force_login(inventorizing_user)
    response = client.post(reverse("inventory:note-delete", kwargs={"pk": room_note.pk}))

    assert response.status_code == 204
    assert not Note.objects.filter(pk=room_note.pk).exists()


@pytest.mark.django_db
def test_update_note_denied_without_permission(client, plain_user, room_1, inventory_1):
    client.force_login(plain_user)
    url = reverse("inventory:note-update", kwargs={"obj_type": "room", "obj_uuid": room_1.uuid})
    response = client.post(url, {"text": "sneaky"}, headers={"HX-Request": "true"})

    assert response["HX-Refresh"] == "true"
    assert not Note.objects.exists()


@pytest.mark.django_db
def test_get_note_btn_denied_without_permission(client, plain_user, room_1):
    client.force_login(plain_user)
    url = reverse("inventory:get_note_btn", kwargs={"obj_type": "room", "obj_uuid": room_1.uuid})
    response = client.get(url, headers={"HX-Request": "true"})

    assert response["HX-Refresh"] == "true"


@pytest.mark.django_db
def test_note_endpoints_require_login(client, room_note):
    response = client.post(reverse("inventory:note-delete", kwargs={"pk": room_note.pk}))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url
    assert Note.objects.filter(pk=room_note.pk).exists()


@pytest.mark.django_db
def test_note_endpoint_without_htmx_returns_403(client, plain_user, room_note, settings):
    # Not an HTMX request: the guard must produce a real 403 instead of the
    # client-refresh response, whose empty body renders as a blank page.
    # Plain static storage so rendering 403.html needs no staticfiles manifest.
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    client.force_login(plain_user)
    response = client.post(reverse("inventory:note-delete", kwargs={"pk": room_note.pk}))

    assert response.status_code == 403
    assert Note.objects.filter(pk=room_note.pk).exists()


@pytest.fixture
def inventorizing_client(client, inventorizing_user, plain_static):
    client.force_login(inventorizing_user)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["inventory:get_note_btn", "inventory:note-update"])
def test_an_unknown_object_type_is_not_found(inventorizing_client, inventory_1, room_1, view):
    url = reverse(view, kwargs={"obj_type": "printer", "obj_uuid": room_1.uuid})

    assert inventorizing_client.get(url).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["inventory:get_note_btn", "inventory:note-update"])
@pytest.mark.parametrize("obj_type", ["device", "room"])
def test_an_unknown_object_is_not_found(inventorizing_client, inventory_1, view, obj_type):
    url = reverse(view, kwargs={"obj_type": obj_type, "obj_uuid": uuid.uuid4()})

    assert inventorizing_client.get(url).status_code == 404


@pytest.mark.django_db
def test_without_an_active_inventory_the_note_views_are_not_found(inventorizing_client, room_1):
    note = Note.objects.create(text="a note", room=room_1)

    assert inventorizing_client.get(reverse("inventory:get_note_btn", args=["room", room_1.uuid])).status_code == 404
    assert inventorizing_client.post(reverse("inventory:note-update", args=["room", room_1.uuid])).status_code == 404
    assert inventorizing_client.post(reverse("inventory:note-delete", args=[note.pk])).status_code == 404
    assert Note.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_only_notes_of_the_active_inventory_are_deleted(inventorizing_client, inventory_1, device_1, room_1):
    old_inventory = Inventory.objects.create(name="old", is_active=False)
    notes = [
        Note.objects.create(text="old inventory", room=room_1, inventory=old_inventory),
        Note.objects.create(text="outside any inventory", device=device_1),
    ]

    for note in notes:
        response = inventorizing_client.post(reverse("inventory:note-delete", args=[note.pk]))
        assert response.status_code == 204  # with the "No note found" message
        assert Note.objects.filter(pk=note.pk).exists()
