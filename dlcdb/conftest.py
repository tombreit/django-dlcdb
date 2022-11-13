import pytest

from dlcdb.core.models import Device, Room


@pytest.fixture
def room():
    return Room.objects.create(number=88887676777, nickname="Theke")


@pytest.fixture
def lentable_device():
    return Device.objects.create(is_lentable=True)


@pytest.fixture
def plain_device():
    return Device.objects.create()
