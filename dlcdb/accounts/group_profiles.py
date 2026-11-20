# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Group profiles: named lists of permissions that DLCDB ships, as a starting point
for a group. Applying one adds its permissions to the group, which doesn't
remember it; applied again after an update, it adds what is new. Every name is
one of DLCDB's own permissions (``tests/test_group_profiles.py``).

Not users and groups: those stay with whoever the operators trust with them.
"""

from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.contrib.auth.models import Permission
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class GroupProfile:
    key: str
    label: str
    description: str
    names: tuple  # "app_label.codename"

    def permissions(self):
        """The profile's permissions, looked up by app label and codename together."""
        lookups = []
        for name in self.names:
            app_label, codename = name.split(".")
            lookups.append(Q(content_type__app_label=app_label, codename=codename))
        return Permission.objects.filter(reduce(or_, lookups))


def _crud(app_label, *models, actions=("view", "add", "change")):
    return tuple(f"{app_label}.{action}_{model}" for model in models for action in actions)


GROUP_PROFILES = (
    GroupProfile(
        key="daily-work",
        label=_("Daily work"),
        description=_(
            "Devices, lending, licences, persons, rooms and master data; moving, lending, "
            "missing and found devices; inventorying and bulk imports. No decommissioning, no settings."
        ),
        names=(
            *_crud("core", "device"),
            "core.view_lentrecord",
            "core.transition_can_order_device",
            "core.transition_can_locate_device",
            "core.transition_can_relocate_device",
            "core.transition_can_lend_device",
            "core.transition_can_lose_device",
            "core.transition_can_find_device",
            *_crud("core", "licencerecord", "person", "room", "manufacturer", "supplier", "devicetype"),
            "core.view_record",
            *_crud("smallstuff", "assignedthing"),
            "core.can_inventorize",
            "dataexchange.view_importerlist",
        ),
    ),
    GroupProfile(
        key="administration",
        label=_("Administration"),
        description=_(
            "The settings, the lending profiles, units and positions, the tenants and the journal. "
            "Not users and groups."
        ),
        names=(
            "organization.view_branding",
            "organization.change_branding",
            *_crud("core", "organizationalunit", "organizationalposition", actions=("view", "add", "change", "delete")),
            "lending.view_lendingconfiguration",
            "lending.change_lendingconfiguration",
            *_crud("lending", "lendingprofile", actions=("view", "add", "change", "delete")),
            "licenses.view_licensesconfiguration",
            "licenses.change_licensesconfiguration",
            "dataexchange.view_udbsyncconfiguration",
            "dataexchange.change_udbsyncconfiguration",
            "dataexchange.view_udbsyncrun",
            *_crud("tenants", "tenant", actions=("view", "add", "change", "delete")),
            "journal.view_journalentry",
            "journal.delete_journalentry",
        ),
    ),
)

BY_KEY = {profile.key: profile for profile in GROUP_PROFILES}
