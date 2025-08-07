# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dataclasses import dataclass
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ..models.record import Record


@dataclass
class DeviceStateData:
    """
    Represents the current state of a device and the actions that can be performed on it.
    """

    # Current state:
    label: str
    css_classes: str
    title: str | None
    url: str | None
    # Possible actions:
    actions: list


def get_device_state_data(device, *, user=None, app_name=None):
    """
    Return a data structure with the current information about the device and
    currently possible actions that can be performed on it.

    Something like:
    {
        "label": "John Doe (123)",
        "title": "Loan to Johne Dow, Room 123",
        "url": "/admin/core/device/123/change",
        "css_classes": "btn btn-success",
        "actions": [
            {"url": "/admin/core/lostrecord/add?device=123", "label": "Mark as lost"},
            {"url": "/admin/core/lentrecord/add?device=123", "label": "Lend device"},
        ]
    }

    As these possible actions depend on the current state of the device, this could
    be modeled as finite state machine:

    none -> inroom
    inroom -> inroom, lent, lost, removed
    lent -> inroom, lost
    lost -> inroom, removed
    removed -> none
    """

    active_record = device.active_record

    # Current state attributes
    label = active_record.get_record_type_display() if active_record else "No active record"
    css_classes = "btn btn-primary" if active_record else "btn btn-warning disabled"
    url = ""
    title = ""

    if active_record:
        if active_record.record_type == Record.INROOM and app_name == "inventory":
            url = f"{reverse('inventory:inventorize-room', kwargs={'pk': active_record.room.pk})}"
            label = f"{active_record.room.number} {label}"
        elif active_record.record_type == Record.INROOM:
            url = f"{reverse('admin:core_record_changelist')}?device__id__exact={device.pk}"

            if hasattr(active_record, "room") and hasattr(active_record.room, "number"):
                label = f"{active_record.room.number} {label}"
            else:
                # This should not happen for an INROOM record, but some
                # legacy or imported records might not have a room set.
                label = "Room not set!"

            title = _("Previous records for this device")
        elif active_record.record_type == Record.LENT:
            url = reverse("admin:core_lentrecord_change", args=[active_record])
            label = f"{active_record.room.number} {active_record.person}"
            title = _("Edit lending")
        elif active_record.record_type == Record.REMOVED:
            css_classes = "btn btn-warning"
            url = reverse("admin:core_record_change", args=[active_record.device.pk])
            title = _("Show removal record")
        elif active_record.record_type == Record.LOST:
            css_classes = "btn btn-danger"
            url = f"{reverse('admin:core_record_changelist')}?device__id__exact={device.pk}"
            label = active_record.get_record_type_display()
            title = _("Previous records for this device")

    # Possible actions based on the current state
    actions = []

    if active_record:
        allowed_next_states = active_record.get_allowed_next_states()
    else:
        # No active record - use initial states from STATE_TRANSITIONS
        allowed_next_states = Record.STATE_TRANSITIONS.get(None, [])

    # Generate actions for each allowed next state
    for next_state in allowed_next_states:
        if next_state is None:
            continue

        try:
            proxy_model = Record.get_proxy_model_by_record_type(next_state)

            # Construct the permission string: <app_label>.add_<model_name>
            perm_str = f"{proxy_model._meta.app_label}.add_{proxy_model._meta.model_name}"

            if user and user.has_perm(perm_str):
                action_url = f"{proxy_model.get_admin_action_url()}?device={device.pk}"
                action_label = dict(Record.RECORD_TYPE_CHOICES).get(next_state, next_state)

                if next_state == Record.LENT and device.is_lentable:
                    action_url = f"{reverse('admin:core_lentrecord_changelist')}?q={device.uuid}"
                    action_label = _("Lend")
                elif next_state == Record.LENT and not device.is_lentable:
                    continue

                actions.append(
                    {
                        "url": action_url,
                        "label": action_label,
                    }
                )

        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    return DeviceStateData(
        label=label,
        css_classes=css_classes,
        title=title,
        url=url,
        actions=actions,
    )
