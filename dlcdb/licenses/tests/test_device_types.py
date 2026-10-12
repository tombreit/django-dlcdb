# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The licence form and the licence list's type filter offer the same device types:
those whose name starts with a licence prefix.
"""

import pytest

from dlcdb.core.models import DeviceType
from dlcdb.licenses.filters import LicenceRecordFilter
from dlcdb.licenses.forms import LicenseForm


@pytest.mark.django_db
def test_form_and_filter_offer_only_the_licence_device_types():
    licence_types = {
        DeviceType.objects.create(name="Lizenz::Office"),
        DeviceType.objects.create(name="License::Graphics"),
        DeviceType.objects.create(name="Licence::Database"),
    }
    DeviceType.objects.create(name="Notebook")
    DeviceType.objects.create(name="Lizenzserver")

    form = LicenseForm(tenants=[])
    type_filter = LicenceRecordFilter.base_filters["device__device_type"]

    assert set(form.fields["device_type"].queryset) == licence_types
    assert set(type_filter.queryset) == licence_types
