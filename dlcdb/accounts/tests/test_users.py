# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The users in the frontend: the list, the user page, deactivating and reactivating."""

import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from dlcdb.accounts.models import CustomUser
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]


@pytest.fixture
def login(client, make_user):
    """Log in a user without the Staff flag: the pages need no admin access."""

    def _login(*perms):
        user = make_user(*perms, email="editor@example.com")
        client.force_login(user)
        return user

    return _login


@pytest.fixture
def ada():
    """A user in a group that may change persons and sees one tenant."""
    group = Group.objects.create(name="helpdesk")
    group.permissions.add(Permission.objects.get(content_type__app_label="core", codename="change_person"))
    Tenant.objects.create(name="Institute").groups.add(group)
    user = CustomUser.objects.create_user(email="ada@example.com", username="ada", first_name="Ada")
    user.groups.add(group)
    return user


def _set_active(client, user, active, **extra):
    return client.post(reverse("accounts:user_set_active", args=[user.pk]), {"active": "1" if active else "0", **extra})


@pytest.mark.parametrize(("perms", "status"), [((), 403), (("accounts.view_customuser",), 200)])
def test_the_users_need_the_view_permission(client, login, ada, perms, status):
    login(*perms)
    assert client.get(reverse("accounts:users")).status_code == status
    assert client.get(reverse("accounts:user_detail", args=[ada.pk])).status_code == status


def test_the_list_finds_users_by_status(client, login, ada):
    login("accounts.view_customuser")
    CustomUser.objects.create_user(email="gone@example.com", username="gone", is_active=False)

    response = client.get(reverse("accounts:users"), {"status": "deactivated"})

    assert [user.email for user in response.context["page_obj"]] == ["gone@example.com"]


def test_the_user_page_shows_groups_permissions_and_tenants(client, login, ada):
    login("accounts.view_customuser")

    response = client.get(reverse("accounts:user_detail", args=[ada.pk]))

    assert [str(p) for p in response.context["permissions"]] == ["Person · change"]
    assert [tenant.name for tenant in response.context["tenants"]] == ["Institute"]
    assert "helpdesk" in response.content.decode()
    assert not response.context["can_change"]


def test_deactivating_needs_the_change_permission(client, login, ada):
    login("accounts.view_customuser")
    assert _set_active(client, ada, False).status_code == 403
    ada.refresh_from_db()
    assert ada.is_active


def test_deactivating_and_reactivating_are_journaled(client, login, ada):
    login("accounts.view_customuser", "accounts.change_customuser")

    _set_active(client, ada, False)
    ada.refresh_from_db()
    assert not ada.is_active
    _set_active(client, ada, True)
    ada.refresh_from_db()
    assert ada.is_active

    assert [entry.summary for entry in JournalEntry.objects.order_by("pk")] == [
        "Deactivated user: ada@example.com",
        "Reactivated user: ada@example.com",
    ]


def test_no_one_deactivates_themselves(client, login):
    editor = login("accounts.view_customuser", "accounts.change_customuser")
    assert _set_active(client, editor, False).status_code == 403
    editor.refresh_from_db()
    assert editor.is_active


def test_deactivating_returns_only_to_a_local_page(client, login, ada):
    login("accounts.view_customuser", "accounts.change_customuser")
    response = _set_active(client, ada, False, next="https://example.org/")
    assert response.url == reverse("accounts:user_detail", args=[ada.pk])


def test_the_settings_page_links_the_users_without_the_staff_flag(client, login):
    login("accounts.view_customuser")
    assert reverse("accounts:users") in client.get(reverse("settings")).content.decode()


def test_a_deactivated_user_may_do_nothing(client, login, ada):
    login("accounts.view_customuser")
    ada.is_active = False
    ada.save()
    response = client.get(reverse("accounts:user_detail", args=[ada.pk]))
    assert "a deactivated user may do nothing" in response.content.decode()


def test_only_a_superuser_deactivates_a_superuser(client, login):
    login("accounts.view_customuser", "accounts.change_customuser")
    root = CustomUser.objects.create_superuser(email="root@example.com", username="root", password="secret")
    assert _set_active(client, root, False).status_code == 403
    root.refresh_from_db()
    assert root.is_active
