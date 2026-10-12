# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The admins stamp the editing user on every save (``AuditBaseModel.stamp_user``).
"""

import pytest
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from dlcdb.core.models import Room
from dlcdb.tenants.models import Tenant


@pytest.fixture
def editor(db):
    return get_user_model().objects.create_superuser(email="editor@example.com", password="secret")


def _admin_request(user):
    request = RequestFactory().post("/")
    request.user = user
    return request


def test_admin_save_stamps_the_editing_user(editor):
    """``CustomBaseModelAdmin.save_model``, which every core admin inherits."""
    room = Room.objects.create(number="A1.23")

    admin_site._registry[Room].save_model(_admin_request(editor), room, form=None, change=True)

    room.refresh_from_db()
    assert room.user == editor
    assert room.username == "editor@example.com"


def test_tenant_admin_save_stamps_the_editing_user(editor):
    tenant = Tenant(name="Institute")

    admin_site._registry[Tenant].save_model(_admin_request(editor), tenant, form=None, change=False)

    tenant.refresh_from_db()
    assert tenant.user == editor
    assert tenant.username == "editor@example.com"
