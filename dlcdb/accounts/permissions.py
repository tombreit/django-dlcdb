# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
DLCDB's own permissions: the ones its code checks, out of the ~230 Django
creates. The group pages offer only these, labelled from the code that checks
them; Django's ``Permission.name`` (English, stored in the database) is never shown.

A permission is DLCDB's own if

- a view guards itself with it (``htmx_permission_required`` records them),
- a menu entry requires it (``required_permission`` in an app's navigation.py),
- a lifecycle transition needs it, or
- it is in ``CHECKED_IN_VIEWS``.

``tests/test_permissions.py`` fails, naming the permission, when the code checks
one that none of these finds.
"""

from dataclasses import dataclass
from importlib import import_module

from django.conf import settings
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from dlcdb.core import lifecycle
from dlcdb.core.models import Device
from dlcdb.core.utils.htmx import guarding_permissions
from dlcdb.theme.context_processors import declared_nav_entries

# Checked inside the body of a page that edits in place, so neither a decorator
# nor a menu entry names them.
CHECKED_IN_VIEWS = (
    "core.change_person",
    "core.change_devicetype",
    "core.change_manufacturer",
    "core.change_supplier",
    "core.change_organizationalunit",
    "core.change_organizationalposition",
    "organization.change_branding",
    "lending.change_lendingconfiguration",
    "lending.change_lendingprofile",
    "licenses.change_licensesconfiguration",
    "dataexchange.change_importerlist",
    "inventory.view_saplist",  # the SAP exports, in core's media view
)

_SLIP_TEMPLATES = _("Its slip templates can read and print everything a lending reaches.")
_REMOVED_IS_FINAL = _("Brings decommissioned devices back; without it, Removed is final.")

# Permissions that reach further than their label says, with the warning shown beside them.
SENSITIVE = {
    "accounts.change_group": _("Can grant every permission listed here, also to their own groups."),
    "accounts.change_customuser": _("Can set any user's password and, in the Django admin, make users superusers."),
    "tenants.change_tenant": _("Can attach their own groups to any tenant, and so see its devices."),
    "lending.add_lendingprofile": _SLIP_TEMPLATES,
    "lending.change_lendingprofile": _SLIP_TEMPLATES,
    "dataexchange.change_udbsyncconfiguration": _(
        "The HR sync creates, changes and deactivates persons as the system configured here says."
    ),
    "core.transition_can_restore_device": _REMOVED_IS_FINAL,
    "core.transition_can_recover_device": _REMOVED_IS_FINAL,
}

# Django's default permissions, in the order a group page lists them.
ACTIONS = {
    "view": pgettext_lazy("permission", "view"),
    "add": pgettext_lazy("permission", "add"),
    "change": pgettext_lazy("permission", "change"),
    "delete": pgettext_lazy("permission", "delete"),
}

# Where a menu entry sits.
MENUS = {"nav_main": _("Menu"), "nav_masterdata": _("Master data"), "nav_settings": _("Settings")}


@dataclass(frozen=True)
class OwnPermission:
    """One of DLCDB's own permissions, as a group page lists it."""

    permission: Permission
    model: str  # the heading it is listed under: "Person"
    action: str  # "change", "Lend / Return", "Inventorize"
    help: str  # its menu entries and what they open, or ""
    warning: str  # why it reaches further than its label says, or ""
    requires: Permission | None  # the model's view permission, granted along with it
    order: tuple  # the position under its heading

    def __str__(self):
        return f"{self.model} · {self.action}"


def permission_name(permission):
    """``"app_label.codename"``, as ``has_perm()`` takes it."""
    return f"{permission.content_type.app_label}.{permission.codename}"


def own_permission_names():
    """``"app_label.codename"`` of every permission DLCDB's code checks."""
    # The URLconf imports every view module, so every view is decorated.
    import_module(settings.ROOT_URLCONF)
    names = guarding_permissions | set(CHECKED_IN_VIEWS) | {t.permission for t in lifecycle.TRANSITIONS}
    for entry in declared_nav_entries():
        names |= _required_permissions(entry)
    return names


def own_permissions():
    """
    DLCDB's own permissions, by model; under a model view, add, change and
    delete come first, then its own permissions. A name without a row in the
    database (a typo; the guard test finds it) is left out.
    """
    names = own_permission_names()
    rows = {permission_name(p): p for p in Permission.objects.select_related("content_type")}
    entries = list(declared_nav_entries())
    own = []
    for name in names & rows.keys():
        menus = [entry for entry in entries if name in _required_permissions(entry)]
        own.append(_describe(rows[name], rows=rows, names=names, menus=menus))
    return sorted(own, key=lambda p: (str(p.model), p.order))


def _describe(permission, *, rows, names, menus):
    name = permission_name(permission)
    opts = permission.content_type.model_class()._meta
    model, requires = opts.verbose_name, None
    transitions = [t for t in lifecycle.TRANSITIONS if t.permission == name]
    action = next((a for a in ACTIONS if permission.codename == get_permission_codename(a, opts)), None)

    if action:
        label, order = ACTIONS[action], (list(ACTIONS).index(action),)
        view = f"{opts.app_label}.{get_permission_codename('view', opts)}"
        if action != "view" and view in names:
            requires = rows[view]
    elif transitions:
        # Lifecycle moves are made on the device page: listed with the device.
        # Lend and return share one permission.
        model = Device._meta.verbose_name
        label = " / ".join(str(t.label) for t in transitions)
        order = (len(ACTIONS), lifecycle.TRANSITIONS.index(transitions[0]))
    else:
        # A permission of its own, such as core.can_inventorize: named after its menu entry.
        label = menus[0]["label"] if menus else permission.codename
        order = (len(ACTIONS) + 1, permission.codename)

    return OwnPermission(
        permission=permission,
        model=capfirst(model),
        action=label,
        help=" · ".join(_menu_help(entry) for entry in menus),
        warning=SENSITIVE.get(name, ""),
        requires=requires,
        order=order,
    )


def _required_permissions(entry):
    """A menu entry's ``required_permission``, any one of which shows it, as a set."""
    required = entry.get("required_permission") or ()
    return {required} if isinstance(required, str) else set(required)


def _menu_help(entry):
    """Where a menu entry sits and what it opens: "Settings › Journal: Sent mails, …"."""
    path = f"{MENUS[entry['slot']]} › {entry['label']}"
    return f"{path}: {entry['description']}" if entry.get("description") else path
