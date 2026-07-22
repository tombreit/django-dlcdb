# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dataclasses import dataclass
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .. import lifecycle
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

    Which actions are possible is decided by the state machine in
    ``dlcdb.core.lifecycle`` (via ``lifecycle.available``); this function only
    presents them for the requesting app.
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
            url = reverse("admin:core_record_change", args=[active_record.pk])
            title = _("Show removal record")
        elif active_record.record_type == Record.LOST:
            css_classes = "btn btn-danger"
            url = f"{reverse('admin:core_record_changelist')}?device__id__exact={device.pk}"
            label = active_record.get_record_type_display()
            title = _("Previous records for this device")

    # Possible actions: whether a transition is offered here -- state, user
    # permission and device precondition -- is decided solely by
    # ``lifecycle.available``. This function only maps each offered transition
    # to a URL and label for the requesting app.
    actions = []
    for transition in lifecycle.available(device, user=user):
        proxy_model = lifecycle.proxy_for(transition.target)

        # Default target: the target proxy model's admin add-view. Admin
        # add-views require is_staff, so mark these as "external" links;
        # surfaces that gate on is_staff (see the assets frontend) use this flag.
        action_url = f"{proxy_model.get_admin_action_url()}?device={device.pk}"
        action_label = transition.label
        external = True

        if transition.target == Record.INROOM and app_name == "assets":
            # Native "Move" module (single-device prefill via ?device=).
            action_url = f"{reverse('assets:relocate')}?device={device.pk}"
            action_label = _("Move")
            external = False
        elif transition.target == Record.LENT:
            if app_name == "assets" and active_record:
                # Native frontend lending flow. LENT is only reachable from an
                # INROOM active record, so active_record.pk is always valid here.
                action_url = reverse("lending:detail", args=[active_record.pk])
                external = False
            else:
                action_url = f"{reverse('admin:core_lentrecord_changelist')}?q={device.uuid}"

        actions.append(
            {
                "url": action_url,
                "label": action_label,
                "external": external,
            }
        )

    return DeviceStateData(
        label=label,
        css_classes=css_classes,
        title=title,
        url=url,
        actions=actions,
    )
