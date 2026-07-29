# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Relocate's device-picker data source: the devices this user can move.

Which states may be moved is not decided here -- it comes from
``lifecycle.LOCALISING_MOVES``, the single declaration that
``core.utils.relocate.relocate_device`` also reads. The picker's own job is to
narrow that to the moves *this* user is permitted to make, so someone who may
only mark lost devices as found is offered the lost ones and nothing else.

``active_record__person`` is selected because the card renders the borrower for
LENT devices.
"""

from django.db.models import Q

from dlcdb.core import lifecycle
from dlcdb.core.models import Device
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.pickers import PickerSource, register_picker_source

# Any of these opens the Move module; which devices it then offers depends on
# which ones the user actually holds.
MOVE_PERMISSIONS = tuple(lifecycle.BY_NAME[name].permission for name in lifecycle.LOCALISING_MOVES)


def move_queryset(request):
    """Tenant-scoped queryset of the devices ``request.user`` may move.

    Shared by the picker and the relocate form, so a device that cannot be
    searched cannot be submitted either.
    """
    states = lifecycle.localisable_states_for(request.user)
    if not states:
        return Device.objects.none()

    lookup = Q(active_record__record_type__in=[state for state in states if state is not None])
    if None in states:
        # A device with no record yet: moving it gives it its first INROOM record.
        lookup |= Q(active_record__isnull=True)

    qs = Device.objects.select_related(
        "active_record__room", "active_record__person", "manufacturer", "device_type"
    ).filter(lookup)
    return tenant_scoped_queryset(qs, request, tenant_field="tenant")


def register():
    register_picker_source(
        PickerSource(
            name="move",
            permissions=MOVE_PERMISSIONS,
            get_queryset=move_queryset,
            search_param="q_device",
            multiple=True,
            exclude_param="devices",
        )
    )
