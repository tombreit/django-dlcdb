# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""``dlcdb.tenants.shortcuts``: the one place that turns group memberships into tenants."""

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory

from dlcdb.core.models import Device
from dlcdb.tenants.middleware import CurrentTenantMiddleware
from dlcdb.tenants.models import Tenant
from dlcdb.tenants.shortcuts import get_user_tenants, limit_tenant_field, tenant_scoped_queryset

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Device.save() writes a QR code image; keep it out of the real media directory."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def member():
    def _make(*tenants, email="member@example.com"):
        user = get_user_model().objects.create_user(email=email, password="secret", username=email.split("@")[0])
        for tenant in tenants:
            group = Group.objects.create(name=f"group-of-{tenant.name}")
            tenant.groups.add(group)
            user.groups.add(group)
        return user

    return _make


def _request(tenants):
    request = RequestFactory().get("/")
    request.tenants = tenants
    return request


def test_anonymous_user_has_no_tenants():
    assert get_user_tenants(AnonymousUser()) == ()


def test_user_without_matching_tenant_has_no_tenants(member):
    assert get_user_tenants(member()) == ()


def test_exactly_one_matching_tenant(tenant, member):
    assert get_user_tenants(member(tenant)) == (tenant,)


def test_one_tenant_via_two_groups_still_counts_once(tenant, member):
    user = member(tenant)
    second_group = Group.objects.create(name="second-group")
    tenant.groups.add(second_group)
    user.groups.add(second_group)

    assert get_user_tenants(user) == (tenant,)


def test_several_matching_tenants_stay_ambiguous(tenant, member):
    # Flexible tenants, step 1: several tenants still mean none.
    other = Tenant.objects.create(name="Other tenant")

    assert get_user_tenants(member(tenant, other)) == ()


def test_superuser_sees_every_tenant(tenant, member):
    # Flexible tenants, step 1: superusers see every tenant, not only their groups'.
    other = Tenant.objects.create(name="Other tenant")
    user = member()
    user.is_superuser = True
    user.save()

    assert set(get_user_tenants(user)) == {tenant, other}


def test_middleware_sets_tenants_and_no_tenant(tenant, member):
    request = RequestFactory().get("/")
    request.user = member(tenant)

    CurrentTenantMiddleware(lambda request: None).process_request(request)

    assert request.tenants == (tenant,)
    assert not hasattr(request, "tenant")


def test_scoped_queryset_keeps_only_devices_of_the_given_tenants(tenant):
    other = Tenant.objects.create(name="Other tenant")
    own = Device.objects.create(edv_id="EDV-OWN", tenant=tenant)
    Device.objects.create(edv_id="EDV-OTHER", tenant=other)
    Device.objects.create(edv_id="EDV-NO-TENANT")

    assert list(tenant_scoped_queryset(Device.objects.all(), _request((tenant,)))) == [own]
    # Devices without tenant are never included, not even with every tenant.
    assert set(tenant_scoped_queryset(Device.objects.all(), _request((tenant, other)))) == set(
        Device.objects.exclude(tenant=None)
    )


def test_scoped_queryset_is_empty_without_tenants(tenant):
    Device.objects.create(edv_id="EDV-OWN", tenant=tenant)

    assert not tenant_scoped_queryset(Device.objects.all(), _request(())).exists()


def test_limit_tenant_field_with_one_tenant_preselects_the_only_option(tenant):
    Tenant.objects.create(name="Other tenant")
    field = forms.ModelChoiceField(queryset=Tenant.objects.all())

    limit_tenant_field(field, (tenant,))

    assert list(field.queryset) == [tenant]
    assert field.initial == tenant
    assert field.empty_label is None


def test_limit_tenant_field_with_several_tenants_requires_a_choice(tenant):
    other = Tenant.objects.create(name="Other tenant")
    Tenant.objects.create(name="Foreign tenant")
    field = forms.ModelChoiceField(queryset=Tenant.objects.all())

    limit_tenant_field(field, (tenant, other))

    assert set(field.queryset) == {tenant, other}
    assert field.initial is None
    assert field.empty_label is not None


def test_limit_tenant_field_without_tenants_offers_nothing(tenant):
    field = forms.ModelChoiceField(queryset=Tenant.objects.all())

    limit_tenant_field(field, ())

    assert not field.queryset.exists()
