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

from dlcdb.core.models import Device, Room, Inventory
from dlcdb.tenants.models import Tenant


@pytest.fixture
def tenant():
    return Tenant.objects.create(name="PytestTenant")


@pytest.fixture
def room():
    return Room.objects.create(number=88887676777, nickname="Bar")


@pytest.fixture
def lentable_device() -> Device:
    return Device.objects.create(is_lentable=True)


@pytest.fixture
def plain_device() -> Device:
    return Device.objects.create()


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
def device_1(db) -> Device:
    return Device.objects.create(sap_id="123")


@pytest.fixture
def device_2(db) -> Device:
    return Device.objects.create(sap_id="foo")


@pytest.fixture
def room_1(db) -> Room:
    return Room.objects.create(number="456")


@pytest.fixture
def room_2(db) -> Room:
    return Room.objects.create(number="789")
