# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone

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


@pytest.mark.django_db
def test_is_unmodified_distinguishes_an_untouched_row_from_an_edited_one():
    """
    auto_now_add and auto_now stamp two separate now() calls on insert, so a new
    row's timestamps are microseconds apart rather than equal -- the tolerance
    window is what makes "never edited" detectable at all.
    """
    device = Device.objects.create()
    assert device.is_unmodified

    device.note = "touched"
    device.save()
    Device.objects.filter(pk=device.pk).update(modified_at=timezone.now() + datetime.timedelta(minutes=5))
    assert not Device.objects.get(pk=device.pk).is_unmodified

    # An unsaved instance has neither stamp; it must not blow up in a template.
    assert not Device().is_unmodified


@pytest.mark.django_db
def test_timeline_dates_are_local_dates():
    """00:30 in Berlin is still the previous day in UTC; the timeline shows the local day."""
    just_after_midnight = datetime.datetime(2026, 10, 10, 22, 30, tzinfo=datetime.UTC)  # 00:30 CEST

    with mock.patch("django.utils.timezone.now", return_value=just_after_midnight):
        licence = Device.objects.create(
            is_licence=True,
            contract_start_date=datetime.date(2026, 10, 1),
            contract_expiration_date=datetime.date(2027, 9, 30),
        )
        dates = {event.event_type: event.date for event in licence.get_timeline()}

    assert dates["added"] == datetime.date(2026, 10, 11)
    assert dates["today"] == datetime.date(2026, 10, 11)
