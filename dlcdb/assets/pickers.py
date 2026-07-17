# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Relocate's device-picker data source: the devices that can be moved.

ORDERED (not yet arrived) and REMOVED (decommissioned) devices are not
physically here to move; LOST stays moveable because a device that turns up is
usually relocated when found. Devices without any record yet are moveable too:
relocating one gives it its first INROOM record (this is the "Set state" path
for record-less devices). ``active_record__person`` is selected because the
card renders the borrower for LENT devices.
"""

from django.db.models import Q

from dlcdb.core.models import Device, Record
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.pickers import PickerSource, register_picker_source

# Active record types that may be relocated.
MOVEABLE_RECORD_TYPES = (Record.INROOM, Record.LENT, Record.LOST)


def move_queryset(request):
    """Tenant-scoped queryset of relocatable devices, shared by the picker and form."""
    qs = Device.objects.select_related(
        "active_record__room", "active_record__person", "manufacturer", "device_type"
    ).filter(Q(active_record__isnull=True) | Q(active_record__record_type__in=MOVEABLE_RECORD_TYPES))
    return tenant_scoped_queryset(qs, request, tenant_field="tenant")


def register():
    register_picker_source(
        PickerSource(
            name="move",
            permission="core.add_inroomrecord",
            get_queryset=move_queryset,
            search_param="q_device",
            multiple=True,
            exclude_param="devices",
        )
    )
