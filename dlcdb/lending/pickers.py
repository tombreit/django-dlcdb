# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Lending's device-picker data source: the set of devices that can be lent.

A device is lendable when its active record is INROOM (physically available),
it is flagged ``is_lentable`` and it is not a licence.
"""

from dlcdb.core import lifecycle
from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.pickers import PickerSource, register_picker_source


def lend_queryset(request):
    """Tenant-scoped queryset of the devices that can be lent right now.

    The "which devices are lendable" rule is defined once, in the lifecycle
    (``lend`` transition: an INROOM device that ``is_lentable``). Sourcing it
    from ``devices_for`` keeps this picker in lockstep with the transition guard
    and the action buttons instead of re-stating the rule.
    """
    qs = lifecycle.devices_for("lend").select_related("active_record__room", "manufacturer", "device_type")
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
