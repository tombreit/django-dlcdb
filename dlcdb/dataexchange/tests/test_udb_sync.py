# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the UDB person sync:

* ``UdbSyncConfiguration`` validation and ``build_request_url`` (no DB needed for
  the URL assembly, but the model is a DB model so we keep it under django_db),
* a sync run against a mocked ``urlopen`` payload, asserting resilience: a
  contract missing the optional email still upserts, while a contract missing a
  required field becomes an ERROR row without aborting the run.
"""

import json
from contextlib import contextmanager
from unittest import mock

import pytest
from django.core.exceptions import ValidationError

from dlcdb.core.models import Person
from dlcdb.dataexchange.models import UdbSyncConfiguration
from dlcdb.dataexchange import udb_sync
from dlcdb.dataexchange.reporting import Outcome


@contextmanager
def _fake_urlopen(payload):
    """Mimic ``urllib.request.urlopen(...)`` used as a context manager."""
    response = mock.Mock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    yield response


def _contract(uuid, first, last, *, email=..., checkin="2024-01-01", drop_checkin=False):
    person = {
        "id": uuid,
        "person_first_name": first,
        "person_last_name": last,
    }
    if email is not ...:
        person["person_email_internal_business"] = email
    contract = {
        "person": person,
        "contract_planned_checkout": "2024-12-31",
        "contract_organization_unit": {"name": "OU-1"},
        "contract_contract_type": {"name": "Mitarbeiter"},
        "contract_organizational_positions": [{"name": "Pos-1"}],
    }
    if not drop_checkin:
        contract["contract_planned_checkin"] = checkin
    return contract


# --- validation / URL assembly ------------------------------------------------


@pytest.mark.django_db
def test_build_request_url_appends_query_to_api_endpoint():
    config = UdbSyncConfiguration.load()
    config.url = "https://udb.example.org/api/external_interface/contracts/"
    url = udb_sync.build_request_url(config)
    # The admin URL is used verbatim; only the query is appended (no path injection).
    assert url.startswith("https://udb.example.org/api/external_interface/contracts/?")
    assert udb_sync.UDB_SYNC_FILTERS in url
    assert f"contract-fields={udb_sync.UDB_SYNC_CONTRACT_FIELDS}" in url
    assert f"person-fields={udb_sync.UDB_SYNC_PERSON_FIELDS}" in url
    assert url.count("/api/external_interface/contracts/") == 1


@pytest.mark.django_db
def test_build_request_url_appends_query_to_json_file():
    config = UdbSyncConfiguration.load()
    config.url = "https://static.example.org/udb.json"
    url = udb_sync.build_request_url(config)
    # JSON-file URL is used as-is; no contracts path is injected.
    assert url.startswith("https://static.example.org/udb.json?")
    assert udb_sync.UDB_SYNC_FILTERS in url
    assert "/api/external_interface/contracts/" not in url


@pytest.mark.django_db
def test_clean_rejects_query_in_url():
    config = UdbSyncConfiguration.load()
    config.url = "https://udb.example.org/?x=1"
    with pytest.raises(ValidationError) as exc:
        config.clean()
    assert "url" in exc.value.message_dict


# --- sync behaviour -----------------------------------------------------------


@pytest.mark.django_db
def test_disabled_sync_returns_none():
    config = UdbSyncConfiguration.load()
    config.enabled = False
    config.save()
    assert udb_sync.import_udb_persons() is None


@pytest.mark.django_db
def test_sync_is_resilient_per_contract():
    config = UdbSyncConfiguration.load()
    config.enabled = True
    config.url = "https://udb.example.org/api/external_interface/contracts/"
    config.save()

    payload = {
        "results": {
            "contracts": [
                _contract("uuid-1", "Ada", "Lovelace", email="ada@example.org"),
                _contract("uuid-2", "Grace", "Hopper"),  # optional email absent
                _contract("uuid-3", "Bad", "Record", drop_checkin=True),  # required field missing
            ]
        }
    }

    with mock.patch.object(udb_sync.urllib.request, "urlopen", return_value=_fake_urlopen(payload)):
        report = udb_sync.import_udb_persons()

    counts = report.counts
    assert counts[Outcome.CREATED] == 2
    assert counts[Outcome.ERROR] == 1

    # Both valid persons were upserted, including the one without an email.
    assert Person.with_softdeleted_objects.filter(udb_person_uuid="uuid-1").exists()
    grace = Person.with_softdeleted_objects.get(udb_person_uuid="uuid-2")
    assert grace.udb_person_email_internal_business in ("", None)
    # The malformed contract did not create a person.
    assert not Person.with_softdeleted_objects.filter(udb_person_uuid="uuid-3").exists()
