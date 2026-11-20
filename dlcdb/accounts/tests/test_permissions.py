# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
DLCDB's own permissions (``dlcdb/accounts/permissions.py``): the guard that every
permission the code checks is collected, so a group page offers it.
"""

import re
from pathlib import Path

import pytest
from django.apps import apps
from django.contrib.auth.models import Permission

from dlcdb.accounts.permissions import (
    CHECKED_IN_VIEWS,
    SENSITIVE,
    own_permission_names,
    own_permissions,
    permission_name,
)
from dlcdb.core.models.abstracts import SingletonBaseModel
from dlcdb.theme.related import get_related_pages

SOURCE = Path(__file__).resolve().parents[2]

# "app_label.codename" quoted in Python, perms.app_label.codename in a template.
QUOTED = re.compile(r"""["']([a-z_]+\.[a-z_]+)["']""")
TEMPLATE_PERMS = re.compile(r"\bperms\.([a-z_]+\.[a-z_]+)")


def _existing():
    return {permission_name(p) for p in Permission.objects.select_related("content_type")}


def _named_in_the_code():
    """Every existing permission the code names, outside tests and migrations."""
    names = set()
    for path in SOURCE.rglob("*"):
        if path.suffix not in (".py", ".html") or {"tests", "migrations"} & set(path.parts):
            continue
        if path == SOURCE / "accounts" / "permissions.py":
            continue  # SENSITIVE names permissions no page checks yet
        names |= set((QUOTED if path.suffix == ".py" else TEMPLATE_PERMS).findall(path.read_text()))
    return names & _existing()


def _derived_by_shared_pages():
    """The settings pages check a singleton's change permission, the related buttons a model's."""
    names = set()
    for model in apps.get_models():
        opts = model._meta
        if issubclass(model, SingletonBaseModel):
            names.add(f"{opts.app_label}.change_{opts.model_name}")
        if pages := get_related_pages(model):
            names |= {pages.permission(action) for action in ("view", "add", "change")}
    return names


@pytest.mark.django_db
def test_every_permission_the_code_checks_is_collected():
    missing = (_named_in_the_code() | _derived_by_shared_pages()) - own_permission_names()
    assert not missing, f"Checked by the code, but not collected; add to CHECKED_IN_VIEWS: {sorted(missing)}"


@pytest.mark.django_db
def test_every_listed_permission_exists():
    listed = own_permission_names() | set(CHECKED_IN_VIEWS) | set(SENSITIVE)
    assert not listed - _existing()


@pytest.mark.django_db
def test_labels_come_from_the_model_the_lifecycle_and_the_menu():
    by_name = {permission_name(p.permission): p for p in own_permissions()}

    change_person = by_name["core.change_person"]
    assert str(change_person) == "Person · change"
    assert change_person.requires.codename == "view_person"

    assert str(by_name["core.transition_can_lend_device"]) == "Device · Lend / Return"
    assert str(by_name["core.can_inventorize"]) == "Inventory · Inventorize"
    assert by_name["core.view_lentrecord"].help == "Menu › Lending"
    assert by_name["tenants.change_tenant"].warning


@pytest.mark.django_db
def test_the_models_follow_the_apps_menus():
    by_name = {permission_name(p.permission): p for p in own_permissions()}
    assert by_name["core.view_device"].area == "Menu"
    assert by_name["core.view_person"].area == "Master data"
    assert by_name["journal.view_journalentry"].area == "Settings › Logs"
    # No menu entry needs a lending profile's permissions: listed last.
    assert by_name["lending.view_lendingprofile"].area == "Other"
    assert own_permissions()[-1].area == "Other"
