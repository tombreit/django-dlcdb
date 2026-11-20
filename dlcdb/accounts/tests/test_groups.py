# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The groups in the frontend: the list, the group page and saving a group."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

GROUP_ADMIN = ("accounts.view_group", "accounts.change_group", "accounts.view_customuser", "accounts.change_customuser")


def _permission(name):
    app_label, codename = name.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def _names(group):
    return {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()}


@pytest.fixture
def login(client, make_user):
    """Log in a user without the Staff flag: the pages need no admin access."""

    def _login(*perms):
        user = make_user(*perms, email="editor@example.com")
        client.force_login(user)
        return user

    return _login


@pytest.fixture
def helpdesk():
    """A group with one of DLCDB's own permissions, one other, a tenant, an active and a deactivated member."""
    group = Group.objects.create(name="helpdesk")
    group.permissions.add(_permission("core.change_person"), _permission("core.add_removedrecord"))
    Tenant.objects.create(name="Institute").groups.add(group)
    User = get_user_model()
    group.user_set.add(
        User.objects.create_user(email="active@example.com", username="active"),
        User.objects.create_user(email="gone@example.com", username="gone", is_active=False),
    )
    return group


def _post(client, group, *, permissions=(), members=None, name=None):
    data = {"name": name or group.name, "permissions": [_permission(perm).pk for perm in permissions]}
    if members is not None:
        data["members"] = [member.pk for member in members]
    return client.post(reverse("accounts:group_detail", args=[group.pk]), data)


@pytest.mark.parametrize(("perms", "status"), [((), 403), (("accounts.view_group",), 200)])
def test_the_groups_need_the_view_permission(client, login, helpdesk, perms, status):
    login(*perms)
    assert client.get(reverse("accounts:groups")).status_code == status
    assert client.get(reverse("accounts:group_detail", args=[helpdesk.pk])).status_code == status


def test_the_list_counts_dlcdbs_own_permissions_and_active_members(client, login, helpdesk, settings):
    settings.AUTH_LDAP_MIRROR_GROUPS = ["helpdesk"]
    login("accounts.view_group")

    response = client.get(reverse("accounts:groups"))

    (row,) = response.context["rows"]
    assert row["permission_count"] == 1
    assert row["group"].member_count == 1
    assert row["ldap"]
    assert "Institute" in response.content.decode()


def test_the_group_page_shows_its_permissions_tenants_and_members(client, login, helpdesk):
    login("accounts.view_group", "accounts.view_customuser")

    response = client.get(reverse("accounts:group_detail", args=[helpdesk.pk]))

    assert response.context["checked"] == {_permission("core.change_person").pk}
    assert response.context["other_permissions"] == ["core.add_removedrecord"]
    assert response.context["form"].fields["permissions"].disabled
    content = response.content.decode()
    assert "Institute" in content
    assert "active@example.com" in content
    assert "gone@example.com" not in content


def test_the_members_need_the_view_permission_for_users(client, login, helpdesk):
    login("accounts.view_group")
    response = client.get(reverse("accounts:group_detail", args=[helpdesk.pk]))
    assert "members" not in response.context["form"].fields
    assert "active@example.com" not in response.content.decode()


def test_saving_needs_the_change_permission(client, login, helpdesk):
    login("accounts.view_group")
    assert _post(client, helpdesk, permissions=["core.view_room"]).status_code == 403
    assert "core.view_room" not in _names(helpdesk)


def test_saving_grants_view_with_change_and_keeps_the_other_permissions(client, login, helpdesk):
    editor = login(*GROUP_ADMIN)

    response = _post(client, helpdesk, permissions=["core.change_room"], members=[editor])

    assert response.status_code == 302
    assert _names(helpdesk) == {"core.change_room", "core.view_room", "core.add_removedrecord"}
    entry = JournalEntry.objects.get(source="accounts.groups")
    assert entry.summary == "Group helpdesk changed"
    assert "Permissions added: Room · change, Room · view" in entry.body
    assert "Permissions removed: Person · change" in entry.body
    assert "Members added: editor@example.com" in entry.body
    assert "Members removed: active@example.com" in entry.body


def test_saving_keeps_the_deactivated_members(client, login, helpdesk):
    editor = login(*GROUP_ADMIN)
    _post(client, helpdesk, members=[editor])
    assert {user.email for user in helpdesk.user_set.all()} == {"editor@example.com", "gone@example.com"}


def test_members_stay_without_the_change_permission_for_users(client, login, helpdesk):
    editor = login("accounts.view_group", "accounts.change_group", "accounts.view_customuser")
    _post(client, helpdesk, members=[editor])
    assert {user.email for user in helpdesk.user_set.all()} == {"active@example.com", "gone@example.com"}


def test_ldap_keeps_the_name_and_members_of_a_mirrored_group(client, login, helpdesk, settings):
    settings.AUTH_LDAP_MIRROR_GROUPS = ["helpdesk"]
    editor = login(*GROUP_ADMIN)

    _post(client, helpdesk, name="renamed", members=[editor], permissions=["core.view_room"])

    helpdesk.refresh_from_db()
    assert helpdesk.name == "helpdesk"
    assert {user.email for user in helpdesk.user_set.all()} == {"active@example.com", "gone@example.com"}
    assert "core.view_room" in _names(helpdesk)


@pytest.mark.parametrize("leave", ["the permission", "the group"])
def test_no_one_locks_themselves_out(client, login, helpdesk, leave):
    """The editor's only way to change groups is this group: neither drop it nor leave."""
    editor = login("accounts.view_customuser", "accounts.change_customuser")
    helpdesk.permissions.add(_permission("accounts.view_group"), _permission("accounts.change_group"))
    helpdesk.user_set.add(editor)
    client.force_login(editor)

    if leave == "the permission":
        response = _post(client, helpdesk, permissions=["accounts.view_group"], members=[editor])
    else:
        response = _post(client, helpdesk, permissions=["accounts.view_group", "accounts.change_group"], members=[])

    assert response.status_code == 200
    assert "You would lose the permission to change groups" in response.content.decode()
    assert "accounts.change_group" in _names(helpdesk)
    assert helpdesk.user_set.contains(editor)


def test_the_tenants_card_ticks_through_the_tenant_matrix(client, login, helpdesk):
    login("accounts.view_group", "tenants.change_tenant")
    tenant = Tenant.objects.get(name="Institute")

    content = client.get(reverse("accounts:group_detail", args=[helpdesk.pk])).content.decode()

    assert reverse("tenants:toggle", args=[tenant.pk, helpdesk.pk]) in content


def test_the_settings_page_links_the_groups_without_the_staff_flag(client, login):
    login("accounts.view_group")
    assert reverse("accounts:groups") in client.get(reverse("settings")).content.decode()


def test_a_new_group_starts_from_a_profile_with_a_tenant_and_members(client, login):
    editor = login("accounts.view_group", "accounts.add_group", *GROUP_ADMIN[2:], "tenants.change_tenant")
    tenant = Tenant.objects.create(name="Library")

    response = client.post(
        reverse("accounts:group_add"),
        {"name": "librarians", "profile": "daily-work", "tenant": tenant.pk, "members": [editor.pk]},
    )

    group = Group.objects.get(name="librarians")
    assert response.url == reverse("accounts:group_detail", args=[group.pk])
    assert {"core.view_device", "core.transition_can_lend_device"} <= _names(group)
    assert "core.transition_can_remove_device" not in _names(group)
    assert list(group.tenant_set.all()) == [tenant]
    assert tenant.history.latest().history_user == editor
    assert list(group.user_set.all()) == [editor]
    entry = JournalEntry.objects.get(source="accounts.groups", event="created")
    assert entry.body == f"Group profile: Daily work\nTenant: Library\nMembers: {editor}"


def test_a_new_group_offers_a_tenant_only_with_the_tenant_permission(client, login):
    login("accounts.view_group", "accounts.add_group")
    form = client.get(reverse("accounts:group_add")).context["form"]
    assert set(form.fields) == {"name", "profile"}


def test_a_profile_adds_its_permissions_and_returns_to_the_group(client, login, helpdesk):
    editor = login(*GROUP_ADMIN)
    url = reverse("accounts:group_detail", args=[helpdesk.pk])

    response = client.post(url, {"name": "helpdesk", "members": [editor.pk], "add_profile": "administration"})

    assert response.url == url
    assert {"tenants.change_tenant", "journal.view_journalentry", "core.add_removedrecord"} <= _names(helpdesk)
    # Copy only: the ticks that were not sent are gone, as with Save.
    assert "core.change_person" not in _names(helpdesk)


def test_deleting_a_group_unticks_its_tenants(client, login, helpdesk):
    login("accounts.view_group", "accounts.delete_group")
    tenant = Tenant.objects.get(name="Institute")

    response = client.post(reverse("accounts:group_delete", args=[helpdesk.pk]))

    assert response.url == reverse("accounts:groups")
    assert not Group.objects.filter(name="helpdesk").exists()
    assert not tenant.groups.exists()
    assert JournalEntry.objects.get(source="accounts.groups", event="deleted").summary == "Group helpdesk deleted"


def test_no_one_deletes_their_only_way_to_change_groups(client, login, helpdesk):
    editor = login("accounts.delete_group")
    helpdesk.permissions.add(_permission("accounts.view_group"), _permission("accounts.change_group"))
    helpdesk.user_set.add(editor)

    client.post(reverse("accounts:group_delete", args=[helpdesk.pk]))

    assert Group.objects.filter(pk=helpdesk.pk).exists()


def test_the_no_tenant_hint_offers_a_new_group_to_who_is_in_none(client, login):
    login("core.view_device", "accounts.add_group", "tenants.change_tenant")
    response = client.get(reverse("settings"))
    assert reverse("accounts:group_add") in response.content.decode()
