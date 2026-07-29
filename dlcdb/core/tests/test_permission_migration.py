# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for ``0073_grant_lifecycle_permissions``.

The migration is the only thing standing between an upgrade and every group
losing every lifecycle button, so it gets tested rather than trusted. Neither
0072 nor 0073 touches the schema -- one is an ``AlterModelOptions``, the other a
``RunPython`` -- so the executor can be driven back and forth inside the test
transaction without any DDL.
"""

import importlib

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from dlcdb.core.lifecycle import TRANSITIONS

# The module name is not a valid identifier, so it cannot be imported directly.
_migration = importlib.import_module("dlcdb.core.migrations.0073_grant_lifecycle_permissions")
MAPPING, NEW_PERMISSIONS = _migration.MAPPING, _migration.NEW_PERMISSIONS

BEFORE = [("core", "0072_alter_record_options")]
AFTER = [("core", "0073_grant_lifecycle_permissions")]

# What the dev fixture's real "edv" group holds today.
EDV_PERMISSIONS = ["add_inroomrecord", "add_lentrecord", "add_lostrecord", "add_orderedrecord"]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)


@pytest.fixture
def at_0072(transactional_db):
    """Rewind to just before the data migration, with the new permissions gone.

    Django never deletes stale ``Permission`` rows, so rewinding alone leaves the
    rows the test database's ``post_migrate`` already created. Deleting them here
    reproduces the situation a real upgrade hits -- and is what makes this a test
    of the ordering problem the migration exists to solve.
    """
    _migrate(BEFORE)
    Permission.objects.filter(
        codename__in=[codename for codename, _ in NEW_PERMISSIONS],
        content_type__app_label="core",
    ).delete()
    yield
    _migrate(AFTER)


def _core_permission(codename):
    return Permission.objects.get(codename=codename, content_type__app_label="core")


def test_mapping_covers_every_transition_permission():
    """Every permission the lifecycle references is either migrated or deliberately not.

    Guards against a transition being added with a permission nobody will ever
    hold, which fails closed and silently hides a button.
    """
    referenced = {t.permission.removeprefix("core.") for t in TRANSITIONS}
    declared = {codename for codename, _ in NEW_PERMISSIONS}
    assert referenced <= declared

    unmigrated = referenced - set(MAPPING)
    assert unmigrated == {"transition_can_restore_device", "transition_can_recover_device"}, (
        "a lifecycle permission is granted to nobody on upgrade; either map it in "
        "MAPPING or add it to this deliberate exception list"
    )


@pytest.mark.django_db(transaction=True)
def test_the_new_permissions_do_not_exist_before_the_migration(at_0072):
    assert not Permission.objects.filter(
        codename="transition_can_relocate_device", content_type__app_label="core"
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_migration_creates_every_new_permission(at_0072):
    _migrate(AFTER)

    record_ct = ContentType.objects.get(app_label="core", model="record")
    for codename, label in NEW_PERMISSIONS:
        permission = Permission.objects.get(codename=codename, content_type=record_ct)
        assert permission.name == label


@pytest.mark.django_db(transaction=True)
def test_an_edv_shaped_group_keeps_what_it_could_already_do(at_0072):
    group = Group.objects.create(name="edv")
    group.permissions.add(*[_core_permission(codename) for codename in EDV_PERMISSIONS])

    _migrate(AFTER)

    granted = set(group.permissions.values_list("codename", flat=True))
    assert {
        "transition_can_order_device",
        "transition_can_locate_device",
        "transition_can_relocate_device",
        "transition_can_find_device",
        "transition_can_lend_device",
        "transition_can_lose_device",
    } <= granted
    # It never held add_removedrecord, so removal stays out of reach ...
    assert "transition_can_remove_device" not in granted
    # ... and the two ways out of REMOVED are granted to nobody by this migration.
    assert "transition_can_restore_device" not in granted
    assert "transition_can_recover_device" not in granted


@pytest.mark.django_db(transaction=True)
def test_a_group_that_can_only_move_devices_does_not_gain_lending(at_0072):
    """The narrowing decision, pinned.

    ``return_lending`` used to be gated on ``add_inroomrecord`` but now shares
    ``transition_can_lend_device`` with ``lend``. Migrating from ``add_inroomrecord`` would
    hand every group that can move a device the right to lend one; the migration
    deliberately maps from ``add_lentrecord`` instead.
    """
    group = Group.objects.create(name="movers")
    group.permissions.add(_core_permission("add_inroomrecord"))

    _migrate(AFTER)

    granted = set(group.permissions.values_list("codename", flat=True))
    assert "transition_can_relocate_device" in granted
    assert "transition_can_lend_device" not in granted


@pytest.mark.django_db(transaction=True)
def test_direct_user_permissions_are_migrated_too(at_0072, django_user_model):
    user = django_user_model.objects.create_user(email="direct@example.com", password="secret")
    user.user_permissions.add(_core_permission("add_lostrecord"))

    _migrate(AFTER)

    assert "transition_can_lose_device" in set(user.user_permissions.values_list("codename", flat=True))


@pytest.mark.django_db(transaction=True)
def test_the_migration_is_idempotent(at_0072):
    group = Group.objects.create(name="edv")
    group.permissions.add(*[_core_permission(codename) for codename in EDV_PERMISSIONS])

    _migrate(AFTER)
    before = set(group.permissions.values_list("codename", flat=True))
    permission_count = Permission.objects.filter(content_type__app_label="core").count()

    _migrate(BEFORE)
    _migrate(AFTER)

    assert set(group.permissions.values_list("codename", flat=True)) == before
    assert Permission.objects.filter(content_type__app_label="core").count() == permission_count


@pytest.mark.django_db(transaction=True)
def test_migrating_backwards_revokes_the_new_permissions(at_0072, django_user_model):
    group = Group.objects.create(name="edv")
    group.permissions.add(*[_core_permission(codename) for codename in EDV_PERMISSIONS])
    user = django_user_model.objects.create_user(email="direct@example.com", password="secret")
    user.user_permissions.add(_core_permission("add_lentrecord"))

    _migrate(AFTER)
    assert "transition_can_lend_device" in set(group.permissions.values_list("codename", flat=True))

    _migrate(BEFORE)

    new_codenames = {codename for codename, _ in NEW_PERMISSIONS}
    assert not new_codenames & set(group.permissions.values_list("codename", flat=True))
    assert not new_codenames & set(user.user_permissions.values_list("codename", flat=True))
    # The old grants are untouched -- reversing must not cost anyone anything.
    assert set(EDV_PERMISSIONS) <= set(group.permissions.values_list("codename", flat=True))
