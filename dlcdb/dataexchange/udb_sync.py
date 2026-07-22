# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Periodic pull sync of persons/contracts from an UDB instance.

Configuration is admin-managed via ``UdbSyncConfiguration`` (endpoint, filters,
API token, enabled toggle). The *requested fields* below are code-owned on
purpose: the per-contract loop reads a fixed set of keys, so the field
projection must not drift from what the importer consumes — that drift is what
previously produced ``KeyError: 'contract_planned_checkin'``.

The sync is resilient per contract: one malformed contract is recorded as an
ERROR row in the returned ``OperationReport`` and the loop continues, instead of
aborting the whole run.
"""

import hashlib
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils.timezone import now

from dlcdb.core.models import OrganizationalUnit, Person, Record
from dlcdb.core.utils.helpers import save_base64img_as_fileimg

from .models import UdbSyncConfiguration, UdbSyncRun
from .reporting import OperationReport, Outcome

logger = logging.getLogger(__name__)

# Seconds to wait for the UDB server to respond before giving up. Prevents a
# hung UDB instance from blocking the periodic huey task indefinitely.
UDB_REQUEST_TIMEOUT = 30

# How many UdbSyncRun rows to keep. The periodic task runs every 10 minutes, so
# without pruning the table would grow ~144 rows/day.
MAX_STORED_SYNC_RUNS = 50

# Code-owned request filters. These are stable business rules, not per-deploy
# config: only contracts in an active/checked-out state, and never test-data
# persons. Kept in code (not the admin) so they cannot drift into pulling test
# or inactive records.
UDB_SYNC_FILTERS = "present=True&person__person_is_test_data=False"

# Code-owned request field projection. These MUST stay in sync with the keys
# read in `_process_contract()` below. They are intentionally not configurable
# in the admin (see UdbSyncConfiguration docstring).
UDB_SYNC_CONTRACT_FIELDS = (
    "person,contract_planned_checkin,contract_planned_checkout,"
    "contract_organization_unit,contract_contract_type,contract_organizational_positions"
)
UDB_SYNC_PERSON_FIELDS = (
    "person_first_name,person_last_name,person_email_internal_business,person_email_private,id,person_image"
)

# Person fields a contract can change. Compared before/after the upsert to tell a
# real UPDATED from an UNCHANGED row. `udb_data_updated_at` is deliberately absent:
# it is stamped on every run and would make every row look changed.
COMPARED_PERSON_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "udb_person_uuid",
    "udb_person_first_name",
    "udb_person_last_name",
    "udb_person_email_internal_business",
    "udb_contract_planned_checkin",
    "udb_contract_planned_checkout",
    "udb_contract_contract_type",
    "udb_contract_organization_unit",
    "udb_contract_organizational_positions",
    "udb_person_image",
    "udb_person_image_hash",
    "organizational_unit",
    "deleted_at",
    "deleted_by",
)


def build_request_url(config):
    """Append the code-owned filters and field projection to the admin-provided URL.

    ``config.url`` is the complete source URL without a query string — either the
    UDB contracts API endpoint or a ready-made JSON dump of the same response.
    The query is appended either way; a static JSON file simply ignores the
    unknown params. The URL is used verbatim (no path injection, trailing slash
    preserved) so the operator stays in full control of the endpoint.
    """
    params = [
        UDB_SYNC_FILTERS,
        f"contract-fields={UDB_SYNC_CONTRACT_FIELDS}",
        f"person-fields={UDB_SYNC_PERSON_FIELDS}",
    ]
    return f"{config.url}?{'&'.join(p for p in params if p)}"


def import_udb_persons():
    """Fetch contracts from the configured UDB instance and upsert Person rows.

    Returns an ``OperationReport`` (``None`` when the sync is disabled).
    """
    config = UdbSyncConfiguration.load()

    if not config.enabled:
        logger.info("[UDB] UDB integration disabled in UdbSyncConfiguration. Exit.")
        return None

    report = OperationReport(operation="UDB person sync", context=config.url)
    try:
        if not config.url:
            raise ValueError("UDB integration is enabled but `url` is not set in UdbSyncConfiguration.")

        request_url = build_request_url(config)
        headers = {"X-API-KEY": config.api_token} if config.api_token else {}
        url_request = urllib.request.Request(request_url, headers=headers)

        thumbnail_size = 400, 300
        person_images_dir = settings.MEDIA_DIR / settings.PERSON_IMAGE_UPLOAD_DIR
        person_images_dir.mkdir(parents=True, exist_ok=True)

        contracts = _fetch_contracts(url_request)

        # Background sync has no request user; attribute the Person upserts to a
        # dedicated "udb-sync" actor so they show up in the admin History tab like
        # manual edits do. Keyed on email (the unique USERNAME_FIELD on CustomUser)
        # so it never collides with another blank-email service user.
        log_user, _ = get_user_model().objects.get_or_create(
            email="udb-sync@dlcdb.invalid",
            defaults={"username": "udb-sync", "is_active": False},
        )

        for index, contract in enumerate(contracts, start=1):
            identifier = _contract_identifier(contract)
            try:
                # Each contract gets its own savepoint: a failed DB write (e.g. a
                # name-uniqueness collision) is rolled back in isolation so it does
                # not poison the transaction for the contracts that follow.
                with transaction.atomic():
                    outcome, detail = _process_contract(
                        contract,
                        person_images_dir=person_images_dir,
                        thumbnail_size=thumbnail_size,
                        log_user_id=log_user.pk,
                    )
                report.add(row=index, identifier=identifier, outcome=outcome, detail=detail)
            except Exception as exc:
                # One bad contract must not abort the whole run.
                logger.error(f"Failed to import UDB contract {identifier}: {exc}")
                report.add(row=index, identifier=identifier, outcome=Outcome.ERROR, detail=str(exc))
    except Exception as exc:
        # A run-level failure (no url, unreachable server, bad JSON). Record it as
        # a failed run so the reason survives, then re-raise for the caller.
        logger.error(f"[UDB] sync failed: {exc}")
        report.add(row=0, identifier="<sync>", outcome=Outcome.ERROR, detail=str(exc))
        _store_run(report)
        raise

    logger.info(f"[UDB] {report.counts_summary()}")
    _store_run(report)
    return report


def _store_run(report):
    """Persist the report as a UdbSyncRun and prune to the most recent runs."""
    report.persist(UdbSyncRun())
    stale_run_ids = list(UdbSyncRun.objects.values_list("pk", flat=True)[MAX_STORED_SYNC_RUNS:])
    UdbSyncRun.objects.filter(pk__in=stale_run_ids).delete()


def _fetch_contracts(url_request):
    """Fetch and parse the UDB response, returning the list of contracts."""
    try:
        logger.debug(f"Requesting {url_request.full_url}")
        with urllib.request.urlopen(url_request, timeout=UDB_REQUEST_TIMEOUT) as response:
            data = response.read()
    except urllib.error.HTTPError as http_error:
        # The server's response body usually explains *why* the request was
        # rejected (e.g. invalid/missing API key, malformed query). Surface it.
        body = http_error.read().decode("utf-8", errors="replace")
        logger.error(
            f"UDB request to {url_request.full_url} failed: "
            f"HTTP {http_error.code} {http_error.reason}. Server response: {body}"
        )
        raise
    except urllib.error.URLError as url_error:
        # DNS failure, connection refused, SSL errors, etc.
        logger.error(
            f"Could not reach UDB at {url_request.full_url}: {url_error.reason}. "
            "Check the UDB Sync Configuration `url` and network connectivity."
        )
        raise
    except TimeoutError:
        logger.error(f"UDB server at {url_request.full_url} did not respond within {UDB_REQUEST_TIMEOUT} seconds.")
        raise

    try:
        udb_obj = json.loads(data.decode("utf-8"))
        return udb_obj["results"]["contracts"]
    except json.JSONDecodeError as decode_error:
        snippet = data.decode("utf-8", errors="replace")[:500]
        logger.error(
            f"UDB response from {url_request.full_url} is not valid JSON: {decode_error}. "
            f"Response starts with: {snippet}"
        )
        raise
    except KeyError as key_error:
        logger.error(
            f"Unexpected UDB JSON structure: missing key {key_error}. Top-level keys present: {list(udb_obj.keys())}"
        )
        raise


def _contract_identifier(contract):
    """Best-effort human identifier for logging/reporting, tolerant of bad data."""
    person = contract.get("person") or {}
    uuid = person.get("id", "?")
    last_name = person.get("person_last_name", "?")
    first_name = person.get("person_first_name", "?")
    return f"uuid={uuid} {last_name}/{first_name}"


def _match_person(udb_person_uuid, first_name, last_name, claim_emails):
    """Find the local Person a UDB contract refers to, most-reliable key first.

    1. Stable remote id (``udb_person_uuid``) — survives name changes.
    2. Claim an un-synced local person (``udb_person_uuid IS NULL``) by email.
    3. Claim an un-synced local person (``udb_person_uuid IS NULL``) by name (iexact).

    Tiers 2/3 are restricted to rows WITHOUT a uuid so we never steal a uuid that
    already belongs to a different UDB person — that reassignment is what produced
    the ``UNIQUE(udb_person_uuid)`` failures. Soft-deleted rows are included so a
    returning person is restored (the upsert defaults reset deleted_at/deleted_by).
    """
    qs = Person.with_softdeleted_objects

    person = qs.filter(udb_person_uuid=udb_person_uuid).first()
    if person:
        return person

    unsynced = qs.filter(udb_person_uuid__isnull=True)
    if claim_emails:
        person = unsynced.filter(email__in=claim_emails).first()
        if person:
            return person

    return unsynced.filter(first_name__iexact=first_name, last_name__iexact=last_name).first()


def _log_admin_history(person, *, log_user_id, action_flag, message):
    """Record a row in the admin History (LogEntry) for a sync-driven change.

    The admin History tab normally only reflects changes made through the admin;
    writing a LogEntry here makes UDB sync edits visible there too, attributed to
    the background "udb-sync" actor.
    """
    LogEntry.objects.log_actions(log_user_id, [person], action_flag, change_message=message, single_object=True)


def _sync_lent_end_dates(person, new_checkout, *, log_user_id):
    """Propagate a changed UDB contract end date onto the person's open lendings.

    Only lendings that opted in (``sync_lent_end_date=True``) and are currently out
    (the device's active LENT record, ``lent_end_date IS NULL``) follow the
    contract. We query ``Record`` directly with explicit filters rather than the
    ``LentRecord`` proxy manager, whose ``device__is_lentable=True`` filter would
    silently drop otherwise-valid lendings.

    The write is intentionally a direct ``save()`` that bypasses
    ``LentRecord.clean()``, so we re-check here the two bounds the form/DB would
    otherwise enforce, and skip (with a log) rather than raise mid-sync:
    - a contract end before the lending's start date makes no sense;
    - a contract end beyond ``MAX_FUTURE_LENT_DESIRED_END_DATE`` (the bound that
      ``LentRecord.clean()`` enforces; the old ``valid_lent_desired_end_date``
      CheckConstraint was removed in migration 0069).

    ``new_checkout`` is None-safe: a cleared contract end is not propagated (we
    never blank out a desired return date).
    """
    if not new_checkout:
        return

    max_future = datetime.strptime(settings.MAX_FUTURE_LENT_DESIRED_END_DATE, "%Y-%m-%d").date()

    lendings = Record.objects.filter(
        person=person,
        record_type=Record.LENT,
        is_active=True,
        lent_end_date__isnull=True,
        sync_lent_end_date=True,
    )
    for lending in lendings:
        if lending.lent_desired_end_date == new_checkout:
            continue
        if lending.lent_start_date and new_checkout < lending.lent_start_date:
            logger.warning(
                f"[UDB] Skipping lent-date sync for record {lending.pk}: "
                f"contract end {new_checkout} precedes lent start {lending.lent_start_date}."
            )
            continue
        if new_checkout > max_future:
            logger.warning(
                f"[UDB] Skipping lent-date sync for record {lending.pk}: "
                f"contract end {new_checkout} exceeds MAX_FUTURE_LENT_DESIRED_END_DATE {max_future}."
            )
            continue

        old = lending.lent_desired_end_date
        lending.lent_desired_end_date = new_checkout
        lending.save(update_fields=["lent_desired_end_date"])
        _log_admin_history(
            lending,
            log_user_id=log_user_id,
            action_flag=CHANGE,
            message=f"Synced desired return date from UDB contract end: {old!r} -> {new_checkout!r}",
        )


def _process_contract(contract, *, person_images_dir, thumbnail_size, log_user_id):
    """Upsert a single Person from one UDB contract.

    Required keys are accessed by subscript (a missing one raises and is reported
    as an ERROR row by the caller). Genuinely optional keys use ``.get()``.
    """
    person = contract["person"]

    # Required: identity + contract dates. A missing key here is a hard error.
    udb_person_uuid = person["id"]
    udb_person_first_name = person["person_first_name"]
    udb_person_last_name = person["person_last_name"]
    udb_contract_planned_checkin = contract["contract_planned_checkin"]
    udb_contract_planned_checkout = contract["contract_planned_checkout"]

    # Optional fields — tolerate absence/None.
    udb_person_email_internal_business = person.get("person_email_internal_business", "")
    udb_person_email_private = person.get("person_email_private", "")
    udb_contract_organization_unit = (contract.get("contract_organization_unit") or {}).get("name", "")
    udb_contract_contract_type = (contract.get("contract_contract_type") or {}).get("name", "")

    positions = contract.get("contract_organizational_positions") or []
    positions = ", ".join(p.get("name", "") for p in positions)

    logger.debug(
        f"Processing UDB person uuid={udb_person_uuid}, "
        f"last name={udb_person_last_name}, first name={udb_person_first_name}"
    )

    udb_organizational_unit = None
    if udb_contract_organization_unit:
        udb_organizational_unit, _ = OrganizationalUnit.objects.get_or_create(name=udb_contract_organization_unit)

    # Match by stable remote id first, then claim an un-synced local person by
    # email, then by name (empty emails are dropped so they never match a
    # NULL/empty local email).
    claim_emails = [e for e in (udb_person_email_internal_business, udb_person_email_private) if e]
    existing = _match_person(udb_person_uuid, udb_person_first_name, udb_person_last_name, claim_emails)

    # Snapshot the compared fields before the upsert (None for a new person).
    # `.values()` returns DB-typed values (foreign keys as ids), so comparing it
    # against the post-save snapshot below is apples-to-apples.
    values_before = (
        Person.with_softdeleted_objects.filter(pk=existing.pk).values(*COMPARED_PERSON_FIELDS).first()
        if existing
        else None
    )

    # The image file path is deterministic (`{uuid}.jpg`), so it never reflects a
    # content change on its own. Hash the source base64 instead: it is both the
    # change signal and the gate that lets us skip rewriting an unchanged image.
    udb_person_image = person.get("person_image")
    udb_person_image_hash = (
        hashlib.md5(udb_person_image.encode("utf-8"), usedforsecurity=False).hexdigest() if udb_person_image else ""
    )
    udb_person_image_path_relative = (
        f"{settings.PERSON_IMAGE_UPLOAD_DIR}/{udb_person_uuid}.jpg" if udb_person_image else ""
    )

    image_changed = udb_person_image and (
        values_before is None or values_before["udb_person_image_hash"] != udb_person_image_hash
    )
    if image_changed:
        logger.debug(f"Converting image for {udb_person_uuid}...")
        save_base64img_as_fileimg(
            base64string=udb_person_image,
            to_filepath=f"{person_images_dir}/{udb_person_uuid}.jpg",
            thumbnail_size=thumbnail_size,
        )

    defaults = dict(
        # Follow UDB: the local name tracks the current UDB name.
        first_name=udb_person_first_name,
        last_name=udb_person_last_name,
        udb_person_uuid=udb_person_uuid,
        udb_person_first_name=udb_person_first_name,
        udb_person_last_name=udb_person_last_name,
        udb_person_email_internal_business=udb_person_email_internal_business,
        udb_contract_planned_checkin=udb_contract_planned_checkin,
        udb_contract_planned_checkout=udb_contract_planned_checkout,
        udb_contract_contract_type=udb_contract_contract_type,
        udb_contract_organization_unit=udb_contract_organization_unit,
        udb_contract_organizational_positions=positions,
        udb_data_updated_at=now(),
        udb_person_image=udb_person_image_path_relative,
        udb_person_image_hash=udb_person_image_hash,
        organizational_unit=udb_organizational_unit,
        deleted_at=None,
        deleted_by=None,
    )

    # Backfill the local email from UDB only when ours is empty, so a person we
    # can actually contact gets an address — but never overwrite a manually
    # maintained local address. The unique constraint still applies; a clash is
    # caught per-contract and reported.
    if udb_person_email_internal_business and (existing is None or not existing.email):
        defaults["email"] = udb_person_email_internal_business

    try:
        if existing is None:
            existing = Person.with_softdeleted_objects.create(**defaults)
            created = True
        else:
            for field, value in defaults.items():
                setattr(existing, field, value)
            existing.save()
            created = False
    except IntegrityError as integrity_error:
        # Surface the original error verbatim — it already names the violated
        # constraint (e.g. core_person.email) — prefixed with the person so the
        # reported row identifies who clashed.
        raise IntegrityError(
            f"Integrity error for {udb_person_last_name}/{udb_person_first_name}: {integrity_error}"
        ) from integrity_error

    if created:
        _log_admin_history(existing, log_user_id=log_user_id, action_flag=ADDITION, message="Added by UDB sync.")
        return Outcome.CREATED, ""

    values_after = Person.with_softdeleted_objects.filter(pk=existing.pk).values(*COMPARED_PERSON_FIELDS).first()
    changes = [
        (field, values_before[field], values_after[field])
        for field in COMPARED_PERSON_FIELDS
        if values_before[field] != values_after[field]
    ]

    # When the contract end date moved, push it onto the person's opted-in open
    # lendings (a brand-new person, handled above, has none). Use the post-save,
    # DB-typed value from `values_after` (a `date`), not the raw JSON string.
    if any(field == "udb_contract_planned_checkout" for field, _old, _new in changes):
        _sync_lent_end_dates(existing, values_after["udb_contract_planned_checkout"], log_user_id=log_user_id)

    if not changes:
        return Outcome.UNCHANGED, ""

    # Build an `old -> new` summary so the admin History tab shows what actually
    # changed, not just which fields. repr() keeps empty/None vs a value
    # unambiguous (e.g. `email: '' -> 'ada@example.org'`).
    change_summary = ", ".join(f"{field}: {old!r} -> {new!r}" for field, old, new in changes)
    _log_admin_history(
        existing,
        log_user_id=log_user_id,
        action_flag=CHANGE,
        message=f"Changed by UDB sync: {change_summary}",
    )

    # The detailed diff is only useful for debugging, so keep it out of routine logs.
    detail = change_summary if settings.DEBUG else ""
    return Outcome.UPDATED, detail
