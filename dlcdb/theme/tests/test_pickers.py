# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the device-picker permission gate.

``theme.views.device_search`` is the single enforcement point for every picker,
and it had no coverage at all. ``PickerSource.permissions`` is a tuple meaning
*any one of these* because a picker can front several lifecycle moves at once:
the "move" source covers locate, relocate and find, which carry three different
permissions and so cannot be expressed as one required string.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from dlcdb.core import lifecycle
from dlcdb.core.models import Device
from dlcdb.theme.pickers import PickerSource, get_picker_source

pytestmark = pytest.mark.django_db


@pytest.fixture
def make_user(db):
    def _make(*codenames, email="picker@example.com"):
        user = get_user_model().objects.create_user(email=email, password="secret", username=email.split("@")[0])
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="core"))
        return get_user_model().objects.get(pk=user.pk)  # reset the perm cache

    return _make


def _source(*permissions):
    return PickerSource(
        name="test",
        permissions=permissions,
        get_queryset=lambda request: Device.objects.none(),
        search_param="q",
        multiple=False,
    )


# --- the any-of rule -----------------------------------------------------


def test_any_one_of_the_permissions_grants_access(make_user):
    source = _source("core.can_locate_device", "core.can_relocate_device", "core.can_find_device")

    assert source.grants_access(make_user("can_find_device"))
    assert source.grants_access(make_user("can_relocate_device", email="b@example.com"))


def test_holding_none_of_them_is_refused(make_user):
    source = _source("core.can_locate_device", "core.can_find_device")

    assert not source.grants_access(make_user("can_relocate_device"))


def test_a_single_permission_source_still_behaves_as_before(make_user):
    source = _source("core.can_lend_device")

    assert source.grants_access(make_user("can_lend_device"))
    assert not source.grants_access(make_user("can_relocate_device", email="b@example.com"))


def test_an_empty_permission_tuple_grants_nobody(make_user):
    """Fail closed: a source that forgot to declare permissions opens to no one."""
    assert not _source().grants_access(make_user("can_relocate_device"))


# --- the registered sources track the lifecycle --------------------------


def test_the_registered_sources_use_lifecycle_permissions():
    """Neither picker may invent its own access rule.

    Both used to name a legacy CRUD permission (``core.change_lentrecord``,
    ``core.add_inroomrecord``) chosen independently of the transition table, so a
    grant could open the action button without opening the picker behind it.
    """
    lend = get_picker_source("lend")
    assert lend.permissions == (lifecycle.BY_NAME["lend"].permission,)

    move = get_picker_source("move")
    expected = {lifecycle.BY_NAME[name].permission for name in lifecycle.LOCALISING_MOVES}
    assert set(move.permissions) == expected
