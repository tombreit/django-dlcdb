# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the field history helper: what a device's simple-history records
turn into on the timeline.
"""

import datetime

import pytest
from simple_history.utils import update_change_reason

from dlcdb.core.models import Device, Manufacturer
from dlcdb.theme.field_history import EMPTY, MASKED, build_field_history

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture
def editor(make_user):
    return make_user(email="editor@example.com")


def _save(device, user, **fields):
    """Save ``fields`` as ``user``; outside a request nobody sets the history user."""
    for name, value in fields.items():
        setattr(device, name, value)
    device._history_user = user
    device.save()


def _history(device):
    return build_field_history(device, exclude=Device.FIELD_HISTORY_EXCLUDE, secret=Device.FIELD_HISTORY_SECRET)


def test_newest_entry_comes_first_and_creation_last(device_1, editor):
    _save(device_1, editor, series="Notebook One")

    entries = _history(device_1)

    assert [entry.action for entry in entries] == ["Changed", "Created"]
    assert entries[0].user == editor
    assert entries[-1].changes == []


def test_a_change_lists_each_field_with_its_old_and_new_value(device_1, editor):
    manufacturer = Manufacturer.objects.create(name="Example Computers")
    _save(device_1, editor, manufacturer=manufacturer, purchase_date=datetime.date(2026, 3, 1), is_lentable=True)

    changes = _history(device_1)[0].changes

    # Model order, verbose names; the empty foreign key is "—", not "Deleted manufacturer (pk=None)".
    assert [(change.field, change.old, change.new) for change in changes] == [
        ("Manufacturer", EMPTY, "Example Computers"),
        ("Date of purchase", EMPTY, "2026-03-01"),
        ("Is loanable?", "No", "Yes"),
    ]


def test_a_save_that_touches_only_excluded_fields_adds_no_entry(device_1, editor):
    _save(device_1, editor, username="someone-else")

    assert [entry.action for entry in _history(device_1)] == ["Created"]


def test_secret_fields_show_only_that_they_were_set(device_1, editor):
    _save(device_1, editor, machine_encryption_key="s3cret")

    entries = _history(device_1)

    assert [(change.old, change.new) for change in entries[0].changes] == [(EMPTY, MASKED)]
    assert "s3cret" not in repr(entries)


def test_a_change_reason_keeps_an_entry_without_field_changes(device_1, editor):
    _save(device_1, editor)
    update_change_reason(device_1, "Added subscribers: someone@example.com")

    entry = _history(device_1)[0]

    assert entry.reason == "Added subscribers: someone@example.com"
    assert entry.changes == []


def test_the_history_takes_a_single_query(device_1, editor, django_assert_num_queries):
    _save(device_1, editor, manufacturer=Manufacturer.objects.create(name="Example Computers"))

    with django_assert_num_queries(1):
        entries = _history(device_1)

    assert entries[0].changes[0].new == "Example Computers"
    assert entries[0].user == editor
