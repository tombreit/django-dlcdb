# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The device state badge and its action buttons, for each screen that shows them:
the admin, the assets device page and the inventory search. Which actions a user
gets is ``lifecycle.available``'s decision; this module only labels them and
routes each to its frontend screen, from every one of them. The badge links to a
page of the same surface. ``theme/device/state_btn_group.html`` and the assets
"Set state" dropdown render the result.
"""

from dataclasses import dataclass

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dlcdb.core import lifecycle
from dlcdb.core.models import Record

from .navigation import with_next

# The transitions the assets frontend serves with its own "Move" module rather
# than the device page's forms. The module works out which one applies from the
# device's current state (see ``lifecycle.localise``).
#
# This mirrors ``lifecycle.LOCALISING_MOVES``, which is what the module's picker
# and ``relocate_device`` are built from -- so ``recover`` is absent here for the
# same reason REMOVED is absent there: bringing a decommissioned device back is a
# separate act with its own permission and its own form on the device page. A
# test pins the two against each other.
RELOCATE_TRANSITIONS = set(lifecycle.LOCALISING_MOVES)

# The screens of the frontend: the assets device page and the inventory device
# search. Their badges link to frontend pages, and they order with one click.
# Without an app name (the admin) the badge keeps its admin links.
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


def get_device_state_data(device, *, user=None, app_name=None, redirect_to=None):
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
            {"url": "/assets/relocate/?device=123", "label": "Move", "method": "get"},
            {"url": "/assets/devices/123/state/lose/", "label": "Not locatable", "method": "get"},
        ]
    }

    Which actions are possible is decided by the state machine in
    ``dlcdb.core.lifecycle`` (via ``lifecycle.available``); this function only
    presents them for the requesting app.

    ``redirect_to`` is the URL the device page's forms and Order return to
    afterwards, passed as ``?next=`` (see ``theme.navigation``); the inventory
    search passes its own.
    """

    active_record = device.active_record
    frontend = app_name in FRONTEND_SURFACES

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

        # The admin pages above need is_staff. In the frontend every badge but the
        # inventory's room badge leads to the device page instead, and only for
        # users who may see it.
        opens_room_inventory = active_record.record_type == Record.INROOM and app_name == "inventory"
        if frontend and not opens_room_inventory:
            may_view = user is not None and user.has_perm("core.view_device")
            url = reverse("assets:device_detail", args=[device.pk]) if may_view else ""
            title = _("Device details") if may_view else ""

    # Possible actions: whether a transition is offered here -- state, user
    # permission and device precondition -- is decided solely by
    # ``lifecycle.available``. This function only maps each offered transition
    # to its frontend screen, on every surface, the admin included.
    actions = []
    for transition in lifecycle.available(device, user=user):
        # Default target: the device page's own form for this state change.
        action_url = with_next(reverse("assets:device_transition", args=[device.pk, transition.name]), redirect_to)
        # How the dropdown submits the action: a plain link, or a POST form for
        # Order, which changes state directly without a form page.
        method = "get"

        # Routing is by transition *name*, not by target state: four different
        # moves write an InRoomRecord, and dispatching on the target would
        # collapse them into one button -- labelling a device's recovery from
        # decommission as "Move", say. The label always stays the transition's own.
        if transition.name in RELOCATE_TRANSITIONS:
            # The "Move" module (single-device prefill via ?device=). It
            # dispatches through ``lifecycle.localise``, which picks the right
            # transition for the device's current state.
            action_url = f"{reverse('assets:relocate')}?device={device.pk}"
        elif transition.name == "order":
            if frontend:
                # A POST that writes the ORDERED record and returns to the device page.
                action_url = with_next(reverse("assets:device_order", args=[device.pk]), redirect_to)
                method = "post"
            else:
                # The admin's device list renders these buttons inside its own
                # form, which cannot hold a second one: link to the device page,
                # where ordering is one click.
                action_url = reverse("assets:device_detail", args=[device.pk])
        elif transition.name == "lend":
            # LENT is only reachable from an INROOM active record, so
            # active_record.pk is always valid here.
            action_url = reverse("lending:detail", args=[active_record.pk])
        elif transition.name == "return_lending":
            # Returning is not a relocation: it stamps the lending's end date and
            # only then puts the device back, in the lending form. The source
            # state is LENT, so active_record is always the lending in question.
            action_url = f"{reverse('lending:detail', args=[active_record.pk])}?flow=return"

        actions.append(
            {
                "url": action_url,
                "label": transition.label,
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
