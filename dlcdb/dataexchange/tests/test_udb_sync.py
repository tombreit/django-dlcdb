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
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from dlcdb.core.models import Person
from dlcdb.dataexchange.models import UdbSyncConfiguration, UdbSyncRun
from dlcdb.dataexchange import udb_sync
from dlcdb.dataexchange.reporting import Outcome


def _enable_sync():
    config = UdbSyncConfiguration.load()
    config.enabled = True
    config.url = "https://udb.example.org/api/external_interface/contracts/"
    config.save()
    return config


def _run_with_payload(payload):
    with mock.patch.object(udb_sync.urllib.request, "urlopen", return_value=_fake_urlopen(payload)):
        return udb_sync.import_udb_persons()


@contextmanager
def _fake_urlopen(payload):
    """Mimic ``urllib.request.urlopen(...)`` used as a context manager."""
    response = mock.Mock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    yield response


def _contract(uuid, first, last, *, email=..., checkin="2024-01-01", drop_checkin=False, image=None):
    person = {
        "id": uuid,
        "person_first_name": first,
        "person_last_name": last,
    }
    if email is not ...:
        person["person_email_internal_business"] = email
    if image is not None:
        person["person_image"] = image
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


# --- change detection: CREATED / UNCHANGED / UPDATED --------------------------


@pytest.mark.django_db
def test_second_run_reports_unchanged_not_updated():
    _enable_sync()
    payload = {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}

    first = _run_with_payload(payload)
    assert first.counts[Outcome.CREATED] == 1

    # Same data again: the person already exists and nothing changed.
    second = _run_with_payload(payload)
    assert second.counts[Outcome.UPDATED] == 0
    assert second.counts[Outcome.UNCHANGED] == 1


@pytest.mark.django_db
def test_changed_field_reports_updated(settings):
    _enable_sync()
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}})

    # A new email for the same person -> a real UPDATE. Under DEBUG the changed
    # field name is included in the row detail.
    settings.DEBUG = True
    report = _run_with_payload(
        {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada+new@example.org")]}}
    )
    assert report.counts[Outcome.UPDATED] == 1
    updated_row = next(row for row in report.rows if row.outcome == Outcome.UPDATED)
    assert "udb_person_email_internal_business" in updated_row.detail


# --- matching: uuid-first, claim by email/name --------------------------------


@pytest.mark.django_db
def test_name_change_keeps_single_person_matched_by_uuid():
    """Regression: a UDB name change under the same id must not collide on the
    unique udb_person_uuid. The row is matched by uuid and its name follows UDB."""
    _enable_sync()
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Rima", "Rahal")]}})

    report = _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Rima Maria", "Rahal")]}})

    assert report.counts[Outcome.ERROR] == 0
    assert report.counts[Outcome.UPDATED] == 1
    people = Person.with_softdeleted_objects.filter(udb_person_uuid="uuid-1")
    assert people.count() == 1
    assert people.get().first_name == "Rima Maria"


@pytest.mark.django_db
def test_claims_local_person_by_email():
    """A manually-added local person (no uuid) is adopted when a UDB person with
    the same email appears — no second row is created."""
    _enable_sync()
    local = Person.objects.create(first_name="Augusta", last_name="King", email="ada@example.org")
    assert local.udb_person_uuid is None

    report = _run_with_payload(
        {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}
    )

    assert report.counts[Outcome.CREATED] == 0
    assert report.counts[Outcome.UPDATED] == 1
    assert Person.with_softdeleted_objects.count() == 1
    local.refresh_from_db()
    assert local.udb_person_uuid == "uuid-1"


@pytest.mark.django_db
def test_claims_local_person_by_name_case_insensitive():
    """With no email match, an un-synced local person is claimed by case-insensitive name."""
    _enable_sync()
    local = Person.objects.create(first_name="ada", last_name="lovelace", email="other@example.org")

    report = _run_with_payload(
        {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}
    )

    assert report.counts[Outcome.CREATED] == 0
    assert Person.with_softdeleted_objects.count() == 1
    local.refresh_from_db()
    assert local.udb_person_uuid == "uuid-1"


@pytest.mark.django_db
def test_claim_by_email_ignores_name_mismatch():
    """Email claim works even when the local name differs from UDB (it then follows
    UDB). This is why email is tried before name."""
    _enable_sync()
    local = Person.objects.create(first_name="Augusta", last_name="King", email="ada@example.org")

    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}})

    local.refresh_from_db()
    assert local.udb_person_uuid == "uuid-1"
    assert (local.first_name, local.last_name) == ("Ada", "Lovelace")


@pytest.mark.django_db
def test_does_not_steal_uuid_from_already_synced_homonym():
    """A second UDB person sharing a name with an already-synced person is not
    claimed (claim is restricted to un-synced rows). The name constraint then
    surfaces it as an ERROR row, leaving the original row untouched."""
    _enable_sync()
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "John", "Smith", email="john1@example.org")]}})

    report = _run_with_payload(
        {"results": {"contracts": [_contract("uuid-2", "John", "Smith", email="john2@example.org")]}}
    )

    assert report.counts[Outcome.ERROR] == 1
    assert not Person.with_softdeleted_objects.filter(udb_person_uuid="uuid-2").exists()
    original = Person.with_softdeleted_objects.get(udb_person_uuid="uuid-1")
    assert (original.first_name, original.last_name) == ("John", "Smith")


# --- email backfill -----------------------------------------------------------


@pytest.mark.django_db
def test_blank_local_email_is_backfilled_from_udb():
    """A claimed local person with no email gets the UDB internal-business address."""
    _enable_sync()
    local = Person.objects.create(first_name="Ada", last_name="Lovelace", email=None)

    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}})

    local.refresh_from_db()
    assert local.email == "ada@example.org"


@pytest.mark.django_db
def test_existing_local_email_is_not_overwritten():
    """A manually maintained local email is preserved even if UDB has another one."""
    _enable_sync()
    local = Person.objects.create(first_name="Ada", last_name="Lovelace", email="manual@example.org")

    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="udb@example.org")]}})

    local.refresh_from_db()
    assert local.email == "manual@example.org"
    assert local.udb_person_email_internal_business == "udb@example.org"


# --- admin history (LogEntry) -------------------------------------------------


def _person_log_entries():
    ct = ContentType.objects.get_for_model(Person)
    return LogEntry.objects.filter(content_type=ct)


@pytest.mark.django_db
def test_created_person_writes_addition_history():
    _enable_sync()
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}})

    entry = _person_log_entries().latest("id")
    assert entry.action_flag == ADDITION
    assert entry.user.username == "udb-sync"
    assert "UDB sync" in entry.change_message


@pytest.mark.django_db
def test_updated_person_writes_change_history_with_fields():
    _enable_sync()
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}})
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada+new@example.org")]}})

    entry = _person_log_entries().filter(action_flag=CHANGE).latest("id")
    assert "udb_person_email_internal_business" in entry.change_message
    assert "->" in entry.change_message  # old -> new diff, not just field names
    assert "'ada+new@example.org'" in entry.change_message  # new value is shown


@pytest.mark.django_db
def test_sync_actor_does_not_collide_with_blank_email_user():
    """A pre-existing blank-email service user must not block creating the udb-sync
    actor (email is the unique USERNAME_FIELD on CustomUser)."""
    User = get_user_model()
    User.objects.create(username="huey", email="", is_active=False)  # legacy blank-email actor
    _enable_sync()

    report = _run_with_payload(
        {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}
    )

    assert report.counts[Outcome.ERROR] == 0
    assert User.objects.filter(username="udb-sync").exists()


@pytest.mark.django_db
def test_unchanged_person_writes_no_history():
    _enable_sync()
    payload = {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}
    _run_with_payload(payload)
    before = _person_log_entries().count()

    _run_with_payload(payload)  # nothing changed -> no new history row

    assert _person_log_entries().count() == before


# --- run persistence ----------------------------------------------------------


@pytest.mark.django_db
def test_successful_run_is_persisted():
    _enable_sync()
    _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}})

    run = UdbSyncRun.objects.latest("created_at")
    assert run.status == "success"
    assert "1 created" in run.summary
    assert run.messages


@pytest.mark.django_db
def test_failed_run_is_persisted_with_reason_and_reraises():
    _enable_sync()
    with mock.patch.object(udb_sync, "_fetch_contracts", side_effect=RuntimeError("UDB unreachable")):
        with pytest.raises(RuntimeError):
            udb_sync.import_udb_persons()

    run = UdbSyncRun.objects.latest("created_at")
    assert run.status == "error"
    assert "UDB unreachable" in run.messages


@pytest.mark.django_db
def test_runs_are_pruned_to_the_limit(settings):
    _enable_sync()
    payload = {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", email="ada@example.org")]}}

    for _ in range(udb_sync.MAX_STORED_SYNC_RUNS + 5):
        _run_with_payload(payload)

    assert UdbSyncRun.objects.count() == udb_sync.MAX_STORED_SYNC_RUNS


# --- image change detection ---------------------------------------------------


@pytest.mark.django_db
def test_unchanged_image_is_not_rewritten():
    _enable_sync()
    payload = {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", image="base64-AAA")]}}

    # The save helper is patched out so the test does not need real image bytes;
    # we only care how often a (re)write is attempted.
    with mock.patch.object(udb_sync, "save_base64img_as_fileimg") as save_image:
        _run_with_payload(payload)  # first run: image written once
        second = _run_with_payload(payload)  # same image: nothing to rewrite

    assert save_image.call_count == 1
    assert second.counts[Outcome.UNCHANGED] == 1


@pytest.mark.django_db
def test_changed_image_reports_updated_and_rewrites(settings):
    _enable_sync()
    settings.DEBUG = True

    with mock.patch.object(udb_sync, "save_base64img_as_fileimg") as save_image:
        _run_with_payload({"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", image="base64-AAA")]}})
        report = _run_with_payload(
            {"results": {"contracts": [_contract("uuid-1", "Ada", "Lovelace", image="base64-BBB")]}}
        )

    assert save_image.call_count == 2  # rewritten because the source changed
    assert report.counts[Outcome.UPDATED] == 1
    updated_row = next(row for row in report.rows if row.outcome == Outcome.UPDATED)
    assert "udb_person_image_hash" in updated_row.detail
