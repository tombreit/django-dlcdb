# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
conftest.py: sharing fixtures across multiple files

The conftest.py file serves as a means of providing fixtures for an
entire directory. Fixtures defined in a conftest.py can be used by any
test in that package without needing to import them (pytest will
automatically discover them).

You can have multiple nested directories/packages containing your
tests, and each directory can have its own conftest.py with its own
fixtures, adding on to the ones provided by the conftest.py files in
parent directories.

https://docs.pytest.org/en/latest/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
"""

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django.test import override_settings

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Device, Inventory, Room
from dlcdb.tenants.models import Tenant


@pytest.fixture(autouse=True, scope="session")
def isolated_media_root(tmp_path_factory):
    """
    Saving a device or room writes its QR code to MEDIA_ROOT. Keep those files,
    also the ones of objects from setUpTestData, out of the instance's data/media.
    """
    with override_settings(MEDIA_ROOT=tmp_path_factory.mktemp("media")):
        yield


@pytest.fixture
def plain_static(settings):
    """Plain static storage, so rendering tests need no built staticfiles manifest."""
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def tenant():
    return Tenant.objects.create(name="PytestTenant")


@pytest.fixture
def media_root(settings, tmp_path):
    """A fresh, empty MEDIA_ROOT for tests that inspect the files they write."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def make_user(db):
    """
    Build a user with the given permissions ("app_label.codename") who sees the
    given tenants, through one group per tenant.
    """

    def _make(*perms, tenants=(), is_staff=False, email="user@example.com"):
        user = CustomUser.objects.create_user(
            email=email, password="secret", username=email.split("@")[0], is_staff=is_staff
        )
        for perm in perms:
            app_label, codename = perm.split(".")
            user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=codename))
        for tenant in tenants:
            group, _ = Group.objects.get_or_create(name=f"{tenant.name} members")
            tenant.groups.add(group)
            user.groups.add(group)
        # Fetched anew: has_perm caches the permissions per user object.
        return CustomUser.objects.get(pk=user.pk)

    return _make


@pytest.fixture
def join_tenant(tenant):
    """
    Let a user see the devices of the ``tenant`` fixture. Superusers need it
    too: they see only the tenants of their groups.
    """

    def _join(user):
        group, _ = Group.objects.get_or_create(name="PytestTenant members")
        tenant.groups.add(group)
        user.groups.add(group)
        return user

    return _join


@pytest.fixture
def room():
    return Room.objects.create(number=88887676777, nickname="Bar")


@pytest.fixture
def user():
    return CustomUser.objects.create(username="testuser")


@pytest.fixture
def lentable_device(tenant) -> Device:
    return Device.objects.create(is_lentable=True, tenant=tenant)


@pytest.fixture
def plain_device(tenant) -> Device:
    return Device.objects.create(tenant=tenant)


@pytest.fixture
def inventory_1(db) -> Inventory:
    return Inventory.objects.create(name="inventory_1", is_active=True)


@pytest.fixture
def inventory_2(db) -> Inventory:
    return Inventory.objects.create(name="inventory_2", is_active=True)


@pytest.fixture
def inventory_3(db) -> Inventory:
    return Inventory.objects.create(name="inventory_3", is_active=True)


@pytest.fixture
def device_1(db, tenant) -> Device:
    return Device.objects.create(sap_id="123", tenant=tenant)


@pytest.fixture
def device_2(db, tenant) -> Device:
    return Device.objects.create(sap_id="foo", tenant=tenant)


@pytest.fixture
def room_1(db) -> Room:
    return Room.objects.create(number="456")


@pytest.fixture
def room_2(db) -> Room:
    return Room.objects.create(number="789")


@pytest.fixture
def external_room(db) -> Room:
    return Room.objects.create(number="External", is_external=True)


@pytest.fixture
def test_site(db):
    """Create a test site for URL testing"""
    # Keep a reference to the original site
    original_site = None
    if Site.objects.exists():
        try:
            original_site = Site.objects.get_current()
        except Site.DoesNotExist:
            pass

    # Create our test site
    test_site = Site.objects.create(domain="dlcdb.test", name="DLCDB Test Site")

    # Set the SITE_ID
    from django.conf import settings

    settings.SITE_ID = test_site.id

    yield test_site

    # Clean up: restore original site if it existed
    if original_site:
        settings.SITE_ID = original_site.id
    else:
        # Delete our test site to leave a clean state
        test_site.delete()
