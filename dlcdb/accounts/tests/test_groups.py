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

pytestmark = pytest.mark.django_db

GROUP_ADMIN = ("accounts.view_group", "accounts.change_group", "accounts.view_customuser", "accounts.change_customuser")
NEW_GROUP_ADMIN = (
    "accounts.add_group",
    "accounts.view_customuser",
    "accounts.change_customuser",
    "tenants.change_tenant",
    "tenants.add_tenant",
)


def _permission(name):
    app_label, codename = name.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def _names(group):
    return {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()}


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
    # Every card after the name starts closed.
    assert content.count('<details class="card card-filled mb-3">') == 3


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


@pytest.mark.parametrize(("mirrored", "shown"), [([], True), (["helpdesk"], False)])
def test_the_members_card_links_a_new_user_unless_ldap_sets_them(client, login, helpdesk, settings, mirrored, shown):
    settings.AUTH_LDAP_MIRROR_GROUPS = mirrored
    login(*GROUP_ADMIN, "accounts.add_customuser")
    url = reverse("accounts:group_detail", args=[helpdesk.pk])

    content = client.get(url).content.decode()

    # Leaves the form and returns; related-links.js asks first if anything is unsaved.
    assert (f'href="{reverse("accounts:user_add")}?next={url}"' in content) == shown


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
    content = response.content.decode()
    assert "You would lose the permission to change groups" in content
    # With an error, the cards open: none hides it.
    assert content.count('<details class="card card-filled mb-3" open>') == 3
    assert "accounts.change_group" in _names(helpdesk)
    assert helpdesk.user_set.contains(editor)


def test_saving_ticks_and_unticks_tenants(client, login, helpdesk):
    editor = login(*GROUP_ADMIN, "tenants.change_tenant")
    institute = Tenant.objects.get(name="Institute")
    library = Tenant.objects.create(name="Library")

    client.post(
        reverse("accounts:group_detail", args=[helpdesk.pk]),
        {"name": "helpdesk", "members": [editor.pk], "tenants": [library.pk]},
    )

    assert list(helpdesk.tenant_set.all()) == [library]
    # Like a tick in the tenant matrix: stamped, into each tenant's history.
    assert institute.history.latest().history_user == editor
    assert library.history.latest().history_user == editor
    body = JournalEntry.objects.get(source="accounts.groups").body
    assert "Tenants added: Library" in body
    assert "Tenants removed: Institute" in body


def test_the_settings_page_links_the_groups_without_the_staff_flag(client, login):
    login("accounts.view_group")
    assert reverse("accounts:groups") in client.get(reverse("settings")).content.decode()


def test_a_new_group_is_the_group_page_without_a_group(client, login):
    login(*NEW_GROUP_ADMIN)
    url = reverse("accounts:group_add")

    response = client.get(url)

    assert set(response.context["form"].fields) == {"name", "permissions", "members", "tenants"}
    content = response.content.decode()
    assert response.context["submit_label"] == "Create group"
    # Each profile's button carries its permissions, for accounts/js/group-profiles.js to tick.
    daily_work = {str(profile.label): pks for profile, pks in response.context["profiles"]}["Daily work"]
    assert _permission("core.view_device").pk in daily_work
    assert f'data-profile-permissions="{",".join(map(str, daily_work))}"' in content
    # Adding a tenant leaves the form and returns; related-links.js asks first.
    assert f'href="{reverse("tenants:add")}?next={url}"' in content
    assert "data-related-link" in content


def test_a_new_group_saves_permissions_members_and_tenants(client, login):
    editor = login(*NEW_GROUP_ADMIN)
    library = Tenant.objects.create(name="Library")

    response = client.post(
        reverse("accounts:group_add"),
        {
            "name": "librarians",
            "permissions": [_permission("core.change_room").pk],
            "members": [editor.pk],
            "tenants": [library.pk],
        },
    )

    group = Group.objects.get(name="librarians")
    assert response.url == reverse("accounts:groups")
    assert _names(group) == {"core.change_room", "core.view_room"}
    assert list(group.user_set.all()) == [editor]
    assert list(group.tenant_set.all()) == [library]
    assert library.history.latest().history_user == editor
    entry = JournalEntry.objects.get(source="accounts.groups", event="created")
    assert entry.summary == "Group librarians created"
    assert entry.body == (
        "Permissions added: Room · change, Room · view\nMembers added: editor@example.com\nTenants added: Library"
    )


def test_a_new_group_offers_members_and_tenants_only_to_who_may_set_them(client, login):
    login("accounts.add_group", "accounts.view_customuser")
    form = client.get(reverse("accounts:group_add")).context["form"]
    assert set(form.fields) == {"name", "permissions"}


def test_a_new_group_takes_any_name_with_ldap(client, login, settings):
    settings.AUTH_LDAP_MIRROR_GROUPS = True
    login("accounts.add_group")
    form = client.get(reverse("accounts:group_add")).context["form"]
    assert not form.fields["name"].disabled
    assert "exact name" in form.fields["name"].help_text


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
