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

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.db import IntegrityError
from django.utils.timezone import now

from dlcdb.core.models import OrganizationalUnit, Person
from dlcdb.core.utils.helpers import save_base64img_as_fileimg

from .models import UdbSyncConfiguration
from .reporting import OperationReport, Outcome

logger = logging.getLogger(__name__)

# Seconds to wait for the UDB server to respond before giving up. Prevents a
# hung UDB instance from blocking the periodic huey task indefinitely.
UDB_REQUEST_TIMEOUT = 30

# Code-owned request filters. These are stable business rules, not per-deploy
# config: only contracts in an active/checked-out state, and never test-data
# persons. Kept in code (not the admin) so they cannot drift into pulling test
# or inactive records.
UDB_SYNC_FILTERS = "state__in=CHECKED_IN_SIGNATURE_CONFIRMED,CHECKED_OUT_CONFIRMED&person__person_is_test_data=False"

# Code-owned request field projection. These MUST stay in sync with the keys
# read in `_process_contract()` below. They are intentionally not configurable
# in the admin (see UdbSyncConfiguration docstring).
UDB_SYNC_CONTRACT_FIELDS = (
    "person,contract_planned_checkin,contract_planned_checkout,"
    "contract_organization_unit,contract_contract_type,contract_organizational_positions"
)
UDB_SYNC_PERSON_FIELDS = "person_first_name,person_last_name,person_email_internal_business,person_email_private,id"


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

    if not config.url:
        msg = "UDB integration is enabled but `url` is not set in UdbSyncConfiguration."
        logger.error(msg)
        raise ValueError(msg)

    request_url = build_request_url(config)
    headers = {"X-API-KEY": config.api_token} if config.api_token else {}
    url_request = urllib.request.Request(request_url, headers=headers)

    thumbnail_size = 400, 300
    person_images_dir = settings.MEDIA_DIR / settings.PERSON_IMAGE_UPLOAD_DIR
    person_images_dir.mkdir(parents=True, exist_ok=True)

    contracts = _fetch_contracts(url_request)

    report = OperationReport(operation="UDB person sync", context=config.url)
    for index, contract in enumerate(contracts, start=1):
        identifier = _contract_identifier(contract)
        try:
            outcome, detail = _process_contract(
                contract,
                person_images_dir=person_images_dir,
                thumbnail_size=thumbnail_size,
            )
            report.add(row=index, identifier=identifier, outcome=outcome, detail=detail)
        except Exception as exc:
            # One bad contract must not abort the whole run.
            logger.error(f"Failed to import UDB contract {identifier}: {exc}")
            report.add(row=index, identifier=identifier, outcome=Outcome.ERROR, detail=str(exc))

    logger.info(f"[UDB] {report._counts_summary()}")
    return report


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


def _process_contract(contract, *, person_images_dir, thumbnail_size):
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

    udb_person_image_path_relative = ""
    udb_person_image = person.get("person_image")
    if udb_person_image:
        logger.debug(f"Converting image for {udb_person_uuid}...")
        udb_person_image_path_absolute = f"{person_images_dir}/{udb_person_uuid}.jpg"
        udb_person_image_path_relative = f"{settings.PERSON_IMAGE_UPLOAD_DIR}/{udb_person_uuid}.jpg"
        save_base64img_as_fileimg(
            base64string=udb_person_image,
            to_filepath=udb_person_image_path_absolute,
            thumbnail_size=thumbnail_size,
        )

    defaults = dict(
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
        organizational_unit=udb_organizational_unit,
        deleted_at=None,
        deleted_by=None,
    )

    try:
        # Match by firstname/lastname combination (email matching disabled).
        _person, created = Person.with_softdeleted_objects.update_or_create(
            last_name=udb_person_last_name,
            first_name=udb_person_first_name,
            defaults=defaults,
        )
    except IntegrityError as integrity_error:
        raise IntegrityError(
            f"Integrity error for {udb_person_last_name}/{udb_person_first_name}: {integrity_error}. "
            "Hint: first_name/last_name may have changed in UDB."
        ) from integrity_error

    return (Outcome.CREATED if created else Outcome.UPDATED), ""
