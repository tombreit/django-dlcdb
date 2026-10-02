# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""JournalEntry.objects.log(): the defaults every emitter relies on."""

import pytest
from django.utils import translation
from django.utils.translation import gettext_lazy

from dlcdb.journal.models import JournalEntry

pytestmark = pytest.mark.django_db


def test_log_fills_snapshots_and_defaults(make_user, plain_device):
    user = make_user()

    entry = JournalEntry.objects.log(
        source="pytest.topic",
        event="happened",
        summary="Something happened",
        user=user,
        subject=plain_device,
    )

    entry.refresh_from_db()
    assert entry.level == JournalEntry.Level.INFO
    assert entry.timestamp is not None
    assert entry.username == str(user)
    assert entry.content_object == plain_device
    assert entry.object_repr == str(plain_device)
    # The subject's tenant, unless one is given.
    assert entry.tenant == plain_device.tenant


def test_log_without_user_and_subject():
    entry = JournalEntry.objects.log(source="pytest.topic", event="happened", summary="System event")

    assert entry.user is None
    assert entry.username == ""
    assert entry.tenant is None
    assert entry.content_type is None
    assert entry.object_repr == ""


def test_log_explicit_username_and_tenant_win(make_user, plain_device, tenant):
    other_tenant = type(tenant).objects.create(name="Other")

    entry = JournalEntry.objects.log(
        source="pytest.topic",
        event="happened",
        summary="Copied from an old log",
        user=None,
        username="former-user",
        subject=plain_device,
        tenant=other_tenant,
    )

    assert entry.username == "former-user"
    assert entry.tenant == other_tenant


def test_log_stores_lazy_strings_untranslated():
    # "Rooms" has a German translation; the entry must not depend on the
    # language of whoever triggered it.
    with translation.override("de"):
        entry = JournalEntry.objects.log(
            source="pytest.topic", event="happened", summary=gettext_lazy("Rooms"), body=gettext_lazy("Rooms")
        )

    assert entry.summary == "Rooms"
    assert entry.body == "Rooms"


def test_log_cuts_summary_to_field_length():
    entry = JournalEntry.objects.log(source="pytest.topic", event="happened", summary="x" * 300)

    assert len(entry.summary) == 255


def test_levels_sort_by_severity():
    levels = JournalEntry.Level
    assert levels.CRITICAL < levels.ERROR < levels.WARNING < levels.SUCCESS < levels.INFO
