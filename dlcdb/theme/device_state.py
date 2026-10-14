# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The device state badge and its action buttons, for each screen that shows them:
the admin, the assets device page and the inventory search. Which actions a user
gets is ``lifecycle.available``'s decision; this module only labels them and
routes each to the screen's own URL. ``theme/device/state_btn_group.html`` and
the assets "Set state" dropdown render the result.
"""

from dataclasses import dataclass

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dlcdb.core import lifecycle
from dlcdb.core.models import Record

# The transitions the assets frontend serves with its own "Move" module rather
# than an admin add-view. The module works out which one applies from the
# device's current state (see ``lifecycle.localise``).
#
# This mirrors ``lifecycle.LOCALISING_MOVES``, which is what the module's picker
# and ``relocate_device`` are built from -- so ``recover`` is absent here for the
# same reason REMOVED is absent there: bringing a decommissioned device back is a
# separate act with its own permission and its own form on the device page. A
# test pins the two against each other.
RELOCATE_TRANSITIONS = set(lifecycle.LOCALISING_MOVES)

# The screens whose state changes run in the frontend: the assets device page and
# the inventory device search. Without an app name (the admin) the actions open
# the admin's own forms.
FRONTEND_SURFACES = {"assets", "inventory"}


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
    frontend = app_name in FRONTEND_SURFACES
    for transition in lifecycle.available(device, user=user):
        # Default target: in the frontend the device page's own form for this
        # state change, in the admin the target proxy model's add-view.
        if frontend:
            action_url = reverse("assets:device_transition", args=[device.pk, transition.name])
        else:
            proxy_model = lifecycle.proxy_for(transition.target)
            action_url = f"{reverse(f'admin:core_{proxy_model._meta.model_name}_add')}?device={device.pk}"
        action_label = transition.label
        # How the dropdown submits the action: a plain link, or a POST form for
        # native actions that change state directly without a form page.
        method = "get"

        # Routing is by transition *name*, not by target state: four different
        # moves write an InRoomRecord, and dispatching on the target would
        # collapse them into one button -- labelling a device's recovery from
        # decommission as "Move", say. The label always stays the transition's own.
        if transition.name in RELOCATE_TRANSITIONS and frontend:
            # Native "Move" module (single-device prefill via ?device=). It
            # dispatches through ``lifecycle.localise``, which picks the right
            # transition for the device's current state.
            action_url = f"{reverse('assets:relocate')}?device={device.pk}"
        elif transition.name == "order" and frontend:
            # Native frontend action: a POST that writes the ORDERED record and
            # returns to the device page.
            action_url = reverse("assets:device_order", args=[device.pk])
            method = "post"
        elif transition.name == "lend":
            if frontend and active_record:
                # Native frontend lending flow. LENT is only reachable from an
                # INROOM active record, so active_record.pk is always valid here.
                action_url = reverse("lending:detail", args=[active_record.pk])
            else:
                action_url = f"{reverse('admin:core_lentrecord_changelist')}?q={device.uuid}"
        elif transition.name == "return_lending":
            # Returning is not a relocation: it stamps the lending's end date and
            # only then puts the device back. Both surfaces route to the lending
            # form that does that. The source state is LENT, so active_record is
            # always the lending in question.
            if frontend:
                action_url = f"{reverse('lending:detail', args=[active_record.pk])}?flow=return"
            else:
                action_url = reverse("admin:core_lentrecord_change", args=[active_record.pk])

        actions.append(
            {
                "url": action_url,
                "label": action_label,
                "method": method,
            }
        )

    return DeviceStateData(
        label=label,
        css_classes=css_classes,
        title=title,
        url=url,
        actions=actions,
    )
