# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Permission guards for the inventory note endpoints (note button, note
create/edit, note delete). All three are reached over HTMX, so a missing
permission short-circuits with a client refresh instead of a 403 page.
"""

import pytest

from django.contrib.auth.models import Permission
from django.urls import reverse

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Note


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
    response = client.post(reverse("inventory:note-delete", kwargs={"pk": room_note.pk}))

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
    response = client.post(url, {"text": "sneaky"})

    assert response["HX-Refresh"] == "true"
    assert not Note.objects.exists()


@pytest.mark.django_db
def test_get_note_btn_denied_without_permission(client, plain_user, room_1):
    client.force_login(plain_user)
    url = reverse("inventory:get_note_btn", kwargs={"obj_type": "room", "obj_uuid": room_1.uuid})
    response = client.get(url)

    assert response["HX-Refresh"] == "true"


@pytest.mark.django_db
def test_note_endpoints_require_login(client, room_note):
    response = client.post(reverse("inventory:note-delete", kwargs={"pk": room_note.pk}))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url
    assert Note.objects.filter(pk=room_note.pk).exists()
