# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import pytest

from django.urls import reverse

from dlcdb.core.models import Device


@pytest.mark.django_db
def test_device_get_absolute_url():
    """Test the get_absolute_url method for Device class"""

    # Create test devices
    license_device = Device.objects.create(is_licence=True)
    regular_device = Device.objects.create(is_licence=False)

    if license_device:
        expected_license_url = reverse("licenses:edit", kwargs={"license_id": license_device.pk})
        print(f"Testing {license_device.get_absolute_url()=}")
        assert license_device.get_absolute_url() == expected_license_url

    if regular_device:
        # Regular devices do not return an absolute URL for now
        # expected_device_url = reverse("admin:core_device_change", kwargs={"object_id": regular_device.pk})
        expected_device_url = None
        print(f"Testing {regular_device.get_absolute_url()=}")
        assert regular_device.get_absolute_url() == expected_device_url


@pytest.mark.django_db
def test_get_fqdn_url(test_site):
    """Test that get_fqdn_url returns a complete URL with domain"""
    # Create devices
    license_device = Device.objects.create(is_licence=True)
    regular_device = Device.objects.create(is_licence=False)

    # Regular devices do not return an absolute URL for now
    # Get expected URLs - use the actual domain from the fixture
    license_url = f"https://{test_site.domain}{reverse('licenses:edit', kwargs={'license_id': license_device.pk})}"
    print(f"{license_url=}")
    # device_url = (
    #     f"https://{test_site.domain}{reverse('admin:core_device_change', kwargs={'object_id': regular_device.pk})}"
    # )
    device_url = None

    # Test URLs match
    assert license_device.get_fqdn_url() == license_url
    assert regular_device.get_fqdn_url() == device_url
