# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""``get_current_tenant``: the one place that turns group memberships into a tenant."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.messages import get_messages
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import RequestFactory

from dlcdb.tenants.models import Tenant
from dlcdb.tenants.shortcuts import get_current_tenant

pytestmark = pytest.mark.django_db


def _request(user):
    request = RequestFactory().get("/")
    request.user = user
    # Cookie storage needs no session, unlike the default fallback storage.
    request._messages = CookieStorage(request)
    return request


def _errors(request):
    return [str(message) for message in get_messages(request)]


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


def test_anonymous_has_no_tenant_and_no_message():
    request = _request(AnonymousUser())
    assert get_current_tenant(request) is None
    assert _errors(request) == []


def test_superuser_has_no_tenant_and_no_message(tenant, member):
    user = member(tenant)
    user.is_superuser = True
    user.save()
    request = _request(user)
    assert get_current_tenant(request) is None
    assert _errors(request) == []


def test_exactly_one_matching_tenant_is_returned(tenant, member):
    request = _request(member(tenant))
    assert get_current_tenant(request) == tenant
    assert _errors(request) == []


def test_one_tenant_via_two_groups_still_counts_once(tenant, member):
    user = member(tenant)
    second_group = Group.objects.create(name="second-group")
    tenant.groups.add(second_group)
    user.groups.add(second_group)
    request = _request(user)
    assert get_current_tenant(request) == tenant


def test_no_matching_tenant_yields_none_with_one_message(member):
    request = _request(member())
    assert get_current_tenant(request) is None
    # Called twice per request (e.g. middleware and a view): the message is not duplicated.
    assert get_current_tenant(request) is None
    errors = _errors(request)
    assert len(errors) == 1
    assert "Could not find a tenant" in errors[0]


def test_two_matching_tenants_yield_none_with_a_message(tenant, member):
    other = Tenant.objects.create(name="OtherTenant")
    request = _request(member(tenant, other))
    assert get_current_tenant(request) is None
    errors = _errors(request)
    assert len(errors) == 1
    assert "multiple" in errors[0]


def test_a_lookup_error_is_reported_instead_of_raised(tenant, member):
    """Regression: the error path used to raise itself (``messages.error`` without a request)."""
    request = _request(member(tenant))
    with patch.object(Tenant.objects, "filter", side_effect=RuntimeError("boom")):
        assert get_current_tenant(request) is None
    errors = _errors(request)
    assert len(errors) == 1
    assert "boom" in errors[0]
