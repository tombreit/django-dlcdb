# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
JournalEntry.objects: the defaults every emitter relies on in log(), and the
problem counts the dashboard shows.
"""

from datetime import timedelta

import pytest
from django.utils import timezone, translation
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


def _problem(level, **kwargs):
    return JournalEntry.objects.log(source="pytest.topic", event="happened", summary="A problem", level=level, **kwargs)


def test_problem_counts_are_zero_and_most_severe_first_without_entries(tenant):
    levels = JournalEntry.Level

    assert JournalEntry.objects.problem_counts(tenants=[tenant], days=30) == [
        (levels.CRITICAL, 0),
        (levels.ERROR, 0),
        (levels.WARNING, 0),
    ]


def test_problem_counts_ignore_success_and_info(tenant):
    levels = JournalEntry.Level
    _problem(levels.CRITICAL)
    _problem(levels.ERROR)
    _problem(levels.ERROR)
    _problem(levels.WARNING)
    _problem(levels.SUCCESS)
    _problem(levels.INFO)

    assert JournalEntry.objects.problem_counts(tenants=[tenant], days=30) == [
        (levels.CRITICAL, 1),
        (levels.ERROR, 2),
        (levels.WARNING, 1),
    ]


def test_problem_counts_see_own_and_tenantless_entries_only(tenant):
    _problem(JournalEntry.Level.ERROR, tenant=tenant)
    _problem(JournalEntry.Level.ERROR)
    _problem(JournalEntry.Level.ERROR, tenant=type(tenant).objects.create(name="Foreign"))

    counts = dict(JournalEntry.objects.problem_counts(tenants=[tenant], days=30))

    assert counts[JournalEntry.Level.ERROR] == 2


def test_problem_counts_leave_out_older_entries(tenant):
    old = _problem(JournalEntry.Level.ERROR)
    JournalEntry.objects.filter(pk=old.pk).update(timestamp=timezone.now() - timedelta(days=31))
    _problem(JournalEntry.Level.ERROR)

    counts = dict(JournalEntry.objects.problem_counts(tenants=[tenant], days=30))

    assert counts[JournalEntry.Level.ERROR] == 1
