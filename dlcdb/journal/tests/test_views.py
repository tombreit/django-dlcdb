# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The read-only journal list and detail: permission, tenant scoping, filters."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import translation

from dlcdb.core.models import Device
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant

INDEX_URL = "journal:index"
DETAIL_URL = "journal:detail"

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

Level = JournalEntry.Level


@pytest.fixture
def viewer_client(client, make_user, tenant):
    client.force_login(make_user("journal.view_journalentry", tenants=[tenant]))
    return client


def _entry(**kwargs):
    defaults = {"source": "pytest.topic", "event": "happened", "summary": "An entry"}
    return JournalEntry.objects.log(**(defaults | kwargs))


def _listed(response):
    return list(response.context["page_obj"])


def test_index_needs_view_permission(client, make_user, tenant):
    client.force_login(make_user(tenants=[tenant]))

    assert client.get(reverse(INDEX_URL)).status_code == 403


def test_index_lists_own_tenant_and_tenantless_entries_only(viewer_client, tenant):
    own = _entry(summary="Own tenant", tenant=tenant)
    system = _entry(summary="System event")
    foreign = _entry(summary="Foreign tenant", tenant=Tenant.objects.create(name="Foreign"))

    with translation.override("en"):
        response = viewer_client.get(reverse(INDEX_URL))

    assert response.status_code == 200
    assert set(_listed(response)) == {own, system}
    assert foreign.summary not in response.content.decode()
    # The page links itself from the Settings menu.
    assert f'href="{reverse(INDEX_URL)}"' in response.content.decode()


def test_index_htmx_response_is_fragment_only(viewer_client):
    _entry()

    response = viewer_client.get(reverse(INDEX_URL), headers={"HX-Request": "true"})

    assert 'id="journal-list"' in response.content.decode()
    assert "<html" not in response.content.decode()


def test_index_search_matches_summary_body_and_user(viewer_client):
    by_summary = _entry(summary="Printer jam")
    by_body = _entry(summary="Run", body="row 3: printer offline")
    by_user = _entry(summary="Other", username="printer-admin")
    _entry(summary="Unrelated")

    response = viewer_client.get(reverse(INDEX_URL), {"search": "printer"})

    assert set(_listed(response)) == {by_summary, by_body, by_user}


def test_index_filters_by_source_and_event(viewer_client):
    imported = _entry(source="dataexchange.import", event="imported")
    failed = _entry(source="dataexchange.import", event="failed")
    _entry(source="notifications.mail", event="failed")

    by_source = viewer_client.get(reverse(INDEX_URL), {"source": "dataexchange.import"})
    by_both = viewer_client.get(reverse(INDEX_URL), {"source": "dataexchange.import", "event": "failed"})

    assert set(_listed(by_source)) == {imported, failed}
    assert _listed(by_both) == [failed]
    # The dropdowns offer the values found in the journal.
    source_spec = next(spec for spec in by_source.context["filterbar"].specs if spec.param == "source")
    assert [value for value, _label, _checked in source_spec.choices if value] == [
        "dataexchange.import",
        "notifications.mail",
    ]


def test_index_minimum_level_includes_more_severe_levels(viewer_client):
    critical = _entry(level=Level.CRITICAL)
    error = _entry(level=Level.ERROR)
    warning = _entry(level=Level.WARNING)
    _entry(level=Level.SUCCESS)
    _entry(level=Level.INFO)

    response = viewer_client.get(reverse(INDEX_URL), {"level": Level.WARNING})

    assert set(_listed(response)) == {critical, error, warning}


def test_index_sorts_by_severity(viewer_client):
    info = _entry(level=Level.INFO)
    error = _entry(level=Level.ERROR)
    success = _entry(level=Level.SUCCESS)

    response = viewer_client.get(reverse(INDEX_URL), {"ordering": "level"})

    assert _listed(response) == [error, success, info]


def test_index_defaults_to_newest_first(viewer_client):
    first = _entry()
    second = _entry()

    response = viewer_client.get(reverse(INDEX_URL))

    assert _listed(response) == [second, first]


def test_detail_shows_body_and_links_the_subject(viewer_client, tenant):
    licence = Device.objects.create(is_licence=True, tenant=tenant)
    entry = _entry(body="line one\nline two", subject=licence)

    with translation.override("en"):
        response = viewer_client.get(reverse(DETAIL_URL, args=[entry.pk]))

    assert response.status_code == 200
    content = response.content.decode()
    assert "line one\nline two" in content
    assert f'href="{licence.get_absolute_url()}"' in content


def test_detail_names_a_subject_without_page_unlinked(viewer_client, plain_device):
    # A Device that is no licence has no page: get_absolute_url() returns None.
    entry = _entry(subject=plain_device)

    response = viewer_client.get(reverse(DETAIL_URL, args=[entry.pk]))

    content = response.content.decode()
    assert entry.object_repr in content
    assert 'href="None"' not in content


def test_detail_of_a_subject_whose_model_is_gone(viewer_client):
    stale_type = ContentType.objects.create(app_label="retired", model="oldlog")
    entry = _entry()
    JournalEntry.objects.filter(pk=entry.pk).update(content_type=stale_type, object_id=1, object_repr="Old log 1")

    response = viewer_client.get(reverse(DETAIL_URL, args=[entry.pk]))

    assert response.status_code == 200
    assert "Old log 1" in response.content.decode()


def test_detail_is_scoped_like_the_list(viewer_client, tenant):
    foreign = _entry(tenant=Tenant.objects.create(name="Foreign"))
    system = _entry()

    assert viewer_client.get(reverse(DETAIL_URL, args=[foreign.pk])).status_code == 404
    assert viewer_client.get(reverse(DETAIL_URL, args=[system.pk])).status_code == 200


def test_detail_needs_view_permission(client, make_user, tenant):
    client.force_login(make_user(tenants=[tenant]))
    entry = _entry(tenant=tenant)

    assert client.get(reverse(DETAIL_URL, args=[entry.pk])).status_code == 403
