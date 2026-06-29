# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Lending's device-picker data source: the set of devices that can be lent.

A device is lendable when its active record is INROOM (physically available),
it is flagged ``is_lentable`` and it is not a licence. The queryset is annotated
with ``has_lending_profile`` so the card can expose whether an Ausleihzettel
(lending slip) can be printed for the device.
"""

from django.db.models import Exists, OuterRef

from dlcdb.core.models import Device, Record
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.pickers import PickerSource, register_picker_source

from .models import LendingProfile


def lend_queryset(request):
    """Tenant-scoped queryset of available, lentable devices to lend."""
    qs = (
        Device.objects.filter(
            active_record__record_type=Record.INROOM,
            is_lentable=True,
            is_licence=False,
        )
        .select_related("active_record__room", "manufacturer", "device_type")
        .annotate(has_lending_profile=Exists(LendingProfile.objects.filter(device_type=OuterRef("device_type"))))
    )
    return tenant_scoped_queryset(qs, request, tenant_field="tenant")


def register():
    register_picker_source(
        PickerSource(
            name="lend",
            permission="core.change_lentrecord",
            get_queryset=lend_queryset,
            search_param="q",
            multiple=False,
        )
    )
