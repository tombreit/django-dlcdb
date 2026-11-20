# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The groups in the frontend: the list and the group page, read-only."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]


def _permission(name):
    app_label, codename = name.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


@pytest.fixture
def viewer(client, make_user):
    """A user without the Staff flag who may view groups: the pages need no admin access."""
    client.force_login(make_user("accounts.view_group", email="viewer@example.com"))
    return client


@pytest.fixture
def helpdesk():
    """A group with one of DLCDB's own permissions, one other, a tenant, an active and an inactive member."""
    group = Group.objects.create(name="helpdesk")
    group.permissions.add(_permission("core.change_person"), _permission("core.add_removedrecord"))
    Tenant.objects.create(name="Institute").groups.add(group)
    User = get_user_model()
    group.user_set.add(
        User.objects.create_user(email="active@example.com", username="active"),
        User.objects.create_user(email="gone@example.com", username="gone", is_active=False),
    )
    return group


@pytest.mark.parametrize(("perms", "status"), [((), 403), (("accounts.view_group",), 200)])
def test_the_groups_need_the_view_permission(client, make_user, helpdesk, perms, status):
    client.force_login(make_user(*perms))
    assert client.get(reverse("accounts:groups")).status_code == status
    assert client.get(reverse("accounts:group_detail", args=[helpdesk.pk])).status_code == status


def test_the_list_counts_dlcdbs_own_permissions_and_active_members(viewer, helpdesk, settings):
    settings.AUTH_LDAP_MIRROR_GROUPS = ["helpdesk"]

    response = viewer.get(reverse("accounts:groups"))

    (row,) = response.context["rows"]
    assert row["permission_count"] == 1
    assert row["group"].member_count == 1
    assert row["ldap"]
    assert "Institute" in response.content.decode()


def test_the_group_page_shows_its_permissions_tenants_and_members(viewer, helpdesk):
    response = viewer.get(reverse("accounts:group_detail", args=[helpdesk.pk]))

    assert response.context["granted"] == {_permission("core.change_person").pk}
    assert response.context["other_permissions"] == ["core.add_removedrecord"]
    assert not response.context["ldap"]
    content = response.content.decode()
    assert "Institute" in content
    assert "active@example.com" in content
    assert "gone@example.com" not in content


def test_the_settings_page_links_the_groups_without_the_staff_flag(viewer):
    assert reverse("accounts:groups") in viewer.get(reverse("settings")).content.decode()
