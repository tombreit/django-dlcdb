# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Journal cleanup: repeated status entries and old entries."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from dlcdb.journal import cleanup
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

Level = JournalEntry.Level
CLEANUP_URL = reverse("journal:cleanup")
START = timezone.make_aware(datetime.datetime(2026, 8, 18, 4, 40))


def _entry(minutes, **kwargs):
    defaults = {"source": "pytest.topic", "event": "happened", "summary": "An entry"}
    entry = JournalEntry.objects.log(**(defaults | kwargs))
    JournalEntry.objects.filter(pk=entry.pk).update(timestamp=START + datetime.timedelta(minutes=minutes))
    entry.refresh_from_db()
    return entry


def _hr_run(minutes, unchanged, rows, *, level=Level.ERROR):
    """An HR sync run entry: header and counts change from run to run, the rows may not."""
    body = "\n".join(
        [
            f"UDB person sync 2026-08-18 {minutes} — https://udb.example.org",
            f"Unchanged: {unchanged}  Error: {len(rows)}",
            "",
            *rows,
        ]
    )
    return _entry(
        minutes,
        source="dataexchange.hr_sync",
        event="synced",
        level=level,
        summary=f"{unchanged} unchanged, {len(rows)} error",
        body=body,
    )


CONFLICTS = [
    "[row 2] uuid=a Lang/Gabriele  ERROR (UNIQUE constraint failed: core_person.email)",
    "[row 95] uuid=b Frey/Antonia  ERROR (UNIQUE constraint failed: core_person.email)",
]
SHIFTED = [  # the same rows after HR added a person above them
    "[row 3] uuid=a Lang/Gabriele  ERROR (UNIQUE constraint failed: core_person.email)",
    "[row 96] uuid=b Frey/Antonia  ERROR (UNIQUE constraint failed: core_person.email)",
]


def _remaining():
    return set(JournalEntry.objects.exclude(source="journal").values_list("pk", flat=True))


def test_repeated_hr_sync_runs_keep_their_first_and_latest():
    first = _hr_run(0, 256, CONFLICTS)
    for minutes in (10, 20, 30, 40):
        _hr_run(minutes, 256, CONFLICTS)
    other = _hr_run(50, 256, ["[row 7] uuid=c Doe/Pat  UPDATED", *CONFLICTS], level=Level.SUCCESS)
    for minutes in (60, 70):
        _hr_run(minutes, 257, SHIFTED)
    latest = _hr_run(80, 257, SHIFTED)

    [group] = cleanup.repeat_groups()

    assert group.source == "dataexchange.hr_sync"
    assert len(group.removable) == 6
    assert group.first == first.timestamp
    assert group.latest == latest.timestamp
    assert group.summary == "257 unchanged, 2 error"
    cleanup.remove_repeats(user=None)
    assert _remaining() == {first.pk, other.pk, latest.pk}


def test_repeated_anomalies_keep_their_first_and_latest():
    repeated = [
        _entry(minutes * 60, source="notifications.channels", event="log", summary="SMTP down", level=Level.ERROR)
        for minutes in range(4)
    ]
    different = _entry(
        5 * 60, source="notifications.channels", event="log", summary="Mail server slow", level=Level.WARNING
    )

    cleanup.remove_repeats(user=None)

    assert _remaining() == {repeated[0].pk, repeated[-1].pk, different.pk}


def test_events_and_tenant_entries_are_never_repeats(tenant):
    for minutes in range(3):
        _entry(
            minutes, source="notifications.mail", event="sent", summary="Mail sent: Overdue lendings", body="To: a@x"
        )
        _entry(
            minutes,
            source="dataexchange.hr_sync",
            event="synced",
            summary="1 error",
            body="[row 1] x  ERROR",
            tenant=tenant,
        )

    assert cleanup.repeat_groups() == []


def test_removal_is_journaled_with_its_groups(make_user):
    user = make_user()
    for minutes in range(3):
        _hr_run(minutes, 256, CONFLICTS)

    assert cleanup.remove_repeats(user=user) == 1

    entry = JournalEntry.objects.get(source="journal")
    assert (entry.event, entry.summary, entry.user) == ("repeats_removed", "Removed 1 entry (repeats)", user)
    assert "dataexchange.hr_sync synced: 1 removed, kept 2026-08-18 04:40 and 2026-08-18 04:42" in entry.body


def test_nothing_to_remove_writes_no_cleanup_entry():
    assert cleanup.remove_repeats(user=None) == 0
    assert not JournalEntry.objects.exists()


@pytest.mark.parametrize(
    ("moment", "months", "expected"),
    [
        (datetime.datetime(2026, 3, 31, 9, 30), 1, datetime.datetime(2026, 2, 28, 9, 30)),
        (datetime.datetime(2024, 3, 31), 1, datetime.datetime(2024, 2, 29)),
        (datetime.datetime(2026, 1, 15), 12, datetime.datetime(2025, 1, 15)),
        (datetime.datetime(2026, 10, 3), 36, datetime.datetime(2023, 10, 3)),
    ],
)
def test_months_before(moment, months, expected):
    assert cleanup.months_before(moment, months) == expected


@pytest.fixture
def cleaner_client(client, make_user, tenant):
    client.force_login(make_user("journal.view_journalentry", "journal.delete_journalentry", tenants=[tenant]))
    return client


def test_cleanup_needs_the_delete_permission(client, make_user, tenant):
    client.force_login(make_user("journal.view_journalentry", tenants=[tenant]))

    assert client.get(CLEANUP_URL).status_code == 403
    assert client.post(CLEANUP_URL, {"action": "repeats"}).status_code == 403
    assert reverse("journal:cleanup") not in client.get(reverse("journal:index")).content.decode()


def test_index_offers_the_cleanup_with_the_permission(cleaner_client):
    assert f'href="{CLEANUP_URL}"' in cleaner_client.get(reverse("journal:index")).content.decode()


def test_cleanup_page_previews_both_options(cleaner_client):
    for minutes in range(4):
        _hr_run(minutes, 256, CONFLICTS)

    response = cleaner_client.get(CLEANUP_URL)

    assert response.status_code == 200
    assert response.context["repeat_count"] == 2
    assert [option["months"] for option in response.context["age_options"]] == [6, 12, 24, 36]
    assert JournalEntry.objects.count() == 4  # a preview removes nothing


def test_posting_repeats_removes_them(cleaner_client):
    for minutes in range(4):
        _hr_run(minutes, 256, CONFLICTS)

    response = cleaner_client.post(CLEANUP_URL, {"action": "repeats"}, follow=True)

    assert response.redirect_chain[-1][0] == reverse("journal:index")
    assert "Removed 2 repeated entries." in response.content.decode()
    assert JournalEntry.objects.exclude(source="journal").count() == 2


def test_posting_older_removes_only_visible_old_entries(cleaner_client, tenant):
    a_year_ago = -365 * 24 * 60
    old_own = _entry(a_year_ago, tenant=tenant)
    old_system = _entry(a_year_ago)
    old_foreign = _entry(a_year_ago, tenant=Tenant.objects.create(name="Foreign"))
    recent = JournalEntry.objects.log(source="pytest.topic", event="happened", summary="Recent")

    response = cleaner_client.post(CLEANUP_URL, {"action": "older", "months": "6"}, follow=True)

    assert "Removed 2 entries older than" in response.content.decode()
    remaining = set(JournalEntry.objects.values_list("pk", flat=True))
    assert old_own.pk not in remaining and old_system.pk not in remaining
    assert {old_foreign.pk, recent.pk} <= remaining
    assert JournalEntry.objects.get(source="journal").event == "old_entries_removed"


def test_posting_an_invalid_age_removes_nothing(cleaner_client):
    _entry(0)

    response = cleaner_client.post(CLEANUP_URL, {"action": "older", "months": "1"})

    assert response.status_code == 200
    assert response.context["form"].errors
    assert JournalEntry.objects.count() == 1
