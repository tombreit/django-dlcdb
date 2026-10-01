# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tenant admin action "Assign devices without tenant" and its intermediate page."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import ProtectedError
from django.urls import reverse

from dlcdb.core.models import Device
from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

CHANGELIST_URL = "admin:tenants_tenant_changelist"
ASSIGN_URL = "admin:tenants_tenant_assign_devices"
ACTION = "assign_devices_without_tenant"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Device.save() writes a QR code image; keep it out of the real media directory."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def staff_user():
    def _make(*perms):
        user = get_user_model().objects.create_user(
            email="staff@example.com", password="secret", username="staff", is_staff=True
        )
        for perm in perms:
            app_label, codename = perm.split(".")
            user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=codename))
        return user

    return _make


@pytest.fixture
def assigner_client(client, staff_user):
    client.force_login(staff_user("tenants.change_tenant", "core.change_device"))
    return client


def _run_action(client, *tenants):
    return client.post(
        reverse(CHANGELIST_URL),
        {"action": ACTION, "_selected_action": [tenant.pk for tenant in tenants]},
        follow=True,
    )


def test_action_with_one_tenant_redirects_to_the_intermediate_page(assigner_client, tenant):
    response = assigner_client.post(reverse(CHANGELIST_URL), {"action": ACTION, "_selected_action": [tenant.pk]})

    assert response.status_code == 302
    assert response.url == reverse(ASSIGN_URL, args=[tenant.pk])


def test_action_with_several_tenants_shows_an_error(assigner_client, tenant):
    other = Tenant.objects.create(name="Other tenant")

    response = _run_action(assigner_client, tenant, other)

    assert "Please select exactly one tenant." in response.content.decode()


def test_page_lists_only_devices_without_tenant(assigner_client, tenant):
    Device.objects.create(edv_id="EDV-ORPHAN")
    Device.objects.create(edv_id="EDV-OWNED", tenant=tenant)

    response = assigner_client.get(reverse(ASSIGN_URL, args=[tenant.pk]))

    content = response.content.decode()
    assert response.status_code == 200
    assert tenant.name in content
    assert "EDV-ORPHAN" in content
    assert "EDV-OWNED" not in content


def test_post_assigns_only_the_confirmed_devices_without_tenant(assigner_client, tenant):
    confirmed = Device.objects.create(edv_id="EDV-CONFIRMED")
    unchecked = Device.objects.create(edv_id="EDV-UNCHECKED")
    other = Tenant.objects.create(name="Other tenant")
    owned = Device.objects.create(edv_id="EDV-OWNED", tenant=other)

    # `owned` is a crafted pk: it already has a tenant and must keep it.
    response = assigner_client.post(
        reverse(ASSIGN_URL, args=[tenant.pk]), {"device": [confirmed.pk, owned.pk]}, follow=True
    )

    assert "1 device assigned to tenant" in response.content.decode()
    confirmed.refresh_from_db()
    unchecked.refresh_from_db()
    owned.refresh_from_db()
    assert confirmed.tenant == tenant
    assert unchecked.tenant is None
    assert owned.tenant == other

    # Audit fields and simple-history record who assigned the tenant.
    assert confirmed.username == "staff@example.com"
    assert confirmed.history.first().tenant_id == tenant.pk


@pytest.mark.parametrize("perms", [(), ("tenants.change_tenant",), ("core.change_device",)])
def test_action_and_page_need_both_permissions(client, staff_user, tenant, perms):
    client.force_login(staff_user("tenants.view_tenant", *perms))

    changelist = client.get(reverse(CHANGELIST_URL))
    assert ACTION not in changelist.content.decode()
    assert client.get(reverse(ASSIGN_URL, args=[tenant.pk])).status_code == 403


def test_tenant_with_devices_cannot_be_deleted(tenant):
    Device.objects.create(edv_id="EDV-OWNED", tenant=tenant)

    with pytest.raises(ProtectedError):
        tenant.delete()


def test_superuser_without_groups_sees_no_devices_but_can_assign_orphans(client, tenant):
    """Superusers see only their groups' tenants, yet the action still reaches every orphan."""
    Device.objects.create(edv_id="EDV-OWNED", tenant=tenant)
    orphan = Device.objects.create(edv_id="EDV-ORPHAN")
    superuser = get_user_model().objects.create_superuser(email="root@example.com", password="secret", username="root")
    client.force_login(superuser)

    assert "EDV-OWNED" not in client.get(reverse("assets:device_index")).content.decode()

    assert "EDV-ORPHAN" in client.get(reverse(ASSIGN_URL, args=[tenant.pk])).content.decode()
    client.post(reverse(ASSIGN_URL, args=[tenant.pk]), {"device": [orphan.pk]})
    orphan.refresh_from_db()
    assert orphan.tenant == tenant
