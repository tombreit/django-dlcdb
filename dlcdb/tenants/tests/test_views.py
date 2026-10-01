# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The tenant frontend: the group × tenant matrix and the add/edit form."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from dlcdb.core.models import Device
from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Device.save() writes a QR code image; keep it out of the real media directory."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def login(client):
    """Log in a non-staff user with the given permissions: the frontend needs no admin access."""

    def _login(*perms):
        user = get_user_model().objects.create_user(email="ops@example.com", password="secret", username="ops")
        for perm in perms:
            app_label, codename = perm.split(".")
            user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=codename))
        client.force_login(user)
        return client

    return _login


@pytest.fixture
def setup():
    """Tenants A and B; "it" sees both, "ops-a" only A, "helpdesk" none."""
    tenant_a = Tenant.objects.create(name="A")
    tenant_b = Tenant.objects.create(name="B")
    it = Group.objects.create(name="it")
    ops_a = Group.objects.create(name="ops-a")
    helpdesk = Group.objects.create(name="helpdesk")
    tenant_a.groups.add(it, ops_a)
    tenant_b.groups.add(it)
    return tenant_a, tenant_b, it, ops_a, helpdesk


def _matrix(response):
    """The matrix as {group name: [checked per tenant column]}."""
    return {group.name: [checked for _tenant, checked in cells] for group, cells in response.context["rows"]}


@pytest.mark.parametrize(("perms", "status"), [((), 403), (("tenants.view_tenant",), 200)])
def test_matrix_needs_the_view_permission(login, perms, status):
    assert login(*perms).get(reverse("tenants:index")).status_code == status


def test_matrix_shows_which_groups_see_which_tenant(login, setup):
    tenant_a, _tenant_b, it, ops_a, _helpdesk = setup
    Device.objects.create(edv_id="EDV-A", tenant=tenant_a)
    active = get_user_model().objects.create_user(email="active@example.com", username="active")
    inactive = get_user_model().objects.create_user(email="inactive@example.com", username="inactive", is_active=False)
    it.user_set.add(active, inactive)
    ops_a.user_set.add(active)

    response = login("tenants.view_tenant").get(reverse("tenants:index"))

    tenants = response.context["tenants"]
    assert [tenant.name for tenant in tenants] == ["A", "B"]
    assert _matrix(response) == {"helpdesk": [False, False], "it": [True, True], "ops-a": [True, False]}
    assert [tenant.device_count for tenant in tenants] == [1, 0]
    # Users who see the tenant: the active user counts once although two of
    # their groups see A; the inactive user not at all.
    assert [tenant.user_count for tenant in tenants] == [1, 1]
    member_counts = {group.name: group.member_count for group, _cells in response.context["rows"]}
    assert member_counts == {"helpdesk": 0, "it": 1, "ops-a": 1}

    # Viewing only: all six checkboxes disabled and none of them saves.
    content = response.content.decode()
    assert content.count('name="sees"') == 6
    assert "hx-post" not in content


def test_matrix_columns_are_ordered_by_name(login):
    """The counts make it a GROUP BY query, which ignores Meta.ordering."""
    for name in ("zeta", "Alpha", "beta"):
        Tenant.objects.create(name=name).groups.add(Group.objects.get_or_create(name="it")[0])

    response = login("tenants.view_tenant").get(reverse("tenants:index"))

    assert [tenant.name for tenant in response.context["tenants"]] == ["Alpha", "beta", "zeta"]


def _toggle(client, tenant, group, sees):
    """Post one matrix checkbox as htmx does: "sees" only when ticked."""
    return client.post(
        reverse("tenants:toggle", args=[tenant.pk, group.pk]),
        {"sees": "on"} if sees else {},
        headers={"HX-Request": "true"},
    )


def test_matrix_checkboxes_save_each_click(login, setup):
    tenant_a, *_rest = setup
    content = login("tenants.view_tenant", "tenants.change_tenant").get(reverse("tenants:index")).content.decode()

    assert content.count("hx-post=") == 6
    assert f'hx-target="#user-count-{tenant_a.pk}"' in content
    assert f'id="user-count-{tenant_a.pk}"' in content
    assert "<tfoot>" not in content


def test_toggle_needs_the_change_permission(login, setup):
    tenant_a, _tenant_b, _it, _ops_a, helpdesk = setup

    assert _toggle(login("tenants.view_tenant"), tenant_a, helpdesk, sees=True).status_code == 403
    assert helpdesk not in tenant_a.groups.all()


def test_toggle_ticks_and_unticks_and_records_who_did_it(login, setup):
    tenant_a, _tenant_b, _it, _ops_a, helpdesk = setup
    member = get_user_model().objects.create_user(email="member@example.com", username="member")
    helpdesk.user_set.add(member)
    client = login("tenants.view_tenant", "tenants.change_tenant")

    response = _toggle(client, tenant_a, helpdesk, sees=True)

    assert helpdesk in tenant_a.groups.all()
    # The response is the tenant's "users with access" line with the updated count.
    fragment = " ".join(response.content.decode().split())
    assert fragment.startswith(f'<div id="user-count-{tenant_a.pk}"')
    assert "1 user with access" in fragment
    tenant_a.refresh_from_db()
    assert tenant_a.username == "ops@example.com"
    latest = tenant_a.history.first()
    assert latest.history_user.email == "ops@example.com"
    assert helpdesk in {entry.group for entry in latest.groups.all()}

    _toggle(client, tenant_a, helpdesk, sees=False)
    assert helpdesk not in tenant_a.groups.all()


def test_toggle_without_a_change_writes_nothing(login, setup):
    tenant_a, _tenant_b, it, _ops_a, _helpdesk = setup
    modified_at = Tenant.objects.get(pk=tenant_a.pk).modified_at
    history_count = tenant_a.history.count()

    # "it" already sees A: a repeated or late request.
    response = _toggle(login("tenants.view_tenant", "tenants.change_tenant"), tenant_a, it, sees=True)

    assert response.status_code == 200
    assert Tenant.objects.get(pk=tenant_a.pk).modified_at == modified_at
    assert tenant_a.history.count() == history_count


def test_toggle_rejects_get_and_unknown_ids(login, setup):
    tenant_a, _tenant_b, it, *_rest = setup
    client = login("tenants.view_tenant", "tenants.change_tenant")

    assert client.get(reverse("tenants:toggle", args=[tenant_a.pk, it.pk])).status_code == 405
    assert client.post(reverse("tenants:toggle", args=[tenant_a.pk, 99999]), {"sees": "on"}).status_code == 404
    assert client.post(reverse("tenants:toggle", args=[99999, it.pk]), {"sees": "on"}).status_code == 404


@pytest.mark.parametrize(("perms", "status"), [((), 403), (("tenants.add_tenant",), 200)])
def test_add_needs_the_add_permission(login, perms, status):
    assert login(*perms).get(reverse("tenants:add")).status_code == status


def test_add_creates_a_tenant_and_returns_to_the_matrix(login):
    client = login("tenants.view_tenant", "tenants.add_tenant")

    response = client.post(reverse("tenants:add"), {"name": "New", "contact_email": "it@example.com"}, follow=True)

    assert response.redirect_chain == [(reverse("tenants:index"), 302)]
    assert "Tick the groups that should see it." in response.content.decode()
    tenant = Tenant.objects.get(name="New")
    assert tenant.contact_email == "it@example.com"
    assert not tenant.groups.exists()
    assert tenant.username == "ops@example.com"
    created = tenant.history.get()
    assert created.history_type == "+"
    assert created.history_user.email == "ops@example.com"


@pytest.mark.parametrize(("perms", "status"), [((), 403), (("tenants.view_tenant",), 200)])
def test_detail_needs_the_view_permission(login, tenant, perms, status):
    assert login(*perms).get(reverse("tenants:detail", args=[tenant.pk])).status_code == status


def test_detail_is_read_only_without_the_change_permission(login, tenant):
    client = login("tenants.view_tenant")
    url = reverse("tenants:detail", args=[tenant.pk])

    content = client.get(url).content.decode()
    assert "You may view this tenant but do not have permission to edit it." in content
    assert "Changes" in content
    assert "Record data" not in content
    assert client.post(url, {"name": "Renamed", "contact_email": ""}).status_code == 403


def test_detail_renames_and_keeps_the_groups(login, setup):
    tenant_a, *_rest = setup
    client = login("tenants.view_tenant", "tenants.change_tenant")

    client.post(reverse("tenants:detail", args=[tenant_a.pk]), {"name": "A renamed", "contact_email": ""})

    tenant_a.refresh_from_db()
    assert tenant_a.name == "A renamed"
    assert tenant_a.groups.count() == 2
    assert tenant_a.username == "ops@example.com"


@pytest.mark.parametrize(("perms", "status"), [(("tenants.view_tenant",), 403), (("tenants.delete_tenant",), 200)])
def test_delete_needs_the_delete_permission(login, tenant, perms, status):
    assert login(*perms).get(reverse("tenants:delete", args=[tenant.pk])).status_code == status


def test_delete_button_needs_the_delete_permission(login, tenant):
    client = login("tenants.view_tenant", "tenants.change_tenant")

    content = client.get(reverse("tenants:detail", args=[tenant.pk])).content.decode()
    assert reverse("tenants:delete", args=[tenant.pk]) not in content


def test_delete_removes_an_empty_tenant_and_records_it(login, tenant):
    client = login("tenants.view_tenant", "tenants.change_tenant", "tenants.delete_tenant")
    assert (
        reverse("tenants:delete", args=[tenant.pk])
        in client.get(reverse("tenants:detail", args=[tenant.pk])).content.decode()
    )

    response = client.post(reverse("tenants:delete", args=[tenant.pk]), follow=True)

    assert response.redirect_chain == [(reverse("tenants:index"), 302)]
    assert not Tenant.objects.filter(pk=tenant.pk).exists()
    deleted = Tenant.history.get(id=tenant.pk, history_type="-")
    assert deleted.history_user.email == "ops@example.com"


def test_a_tenant_with_devices_cannot_be_deleted(login, tenant):
    Device.objects.create(edv_id="EDV-OWNED", tenant=tenant)
    client = login("tenants.view_tenant", "tenants.change_tenant", "tenants.delete_tenant")
    detail_url = reverse("tenants:detail", args=[tenant.pk])

    content = client.get(detail_url).content.decode()
    assert reverse("tenants:delete", args=[tenant.pk]) not in content
    assert "A tenant with devices cannot be deleted." in content

    response = client.post(reverse("tenants:delete", args=[tenant.pk]), follow=True)
    assert response.redirect_chain == [(detail_url, 302)]
    assert "still has devices and cannot be deleted" in response.content.decode()
    assert Tenant.objects.filter(pk=tenant.pk).exists()
