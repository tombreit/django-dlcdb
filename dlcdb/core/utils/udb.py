# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json
import logging
from django.conf import settings
from django.utils.timezone import now
from django.db import IntegrityError
import urllib.request
import urllib.error

from dlcdb.core.models import Person, OrganizationalUnit
from .helpers import save_base64img_as_fileimg


# Use the project's configured logging (see LOGGING in settings/base.py). The
# `dlcdb` logger hierarchy already routes to the console and sets `propagate=False`,
# so we must NOT add our own handler here — that duplicated every log line.
logger = logging.getLogger(__name__)

# Seconds to wait for the UDB server to respond before giving up. Prevents a
# hung UDB instance from blocking the periodic huey task indefinitely.
UDB_REQUEST_TIMEOUT = 30


def import_udb_persons():
    if not settings.UDB_INTEGRATION:
        logger.info("[UDB] UDB integration disabled via `.env`. Exit.")
        return

    logger.debug("[huey persons utils: import_udb_persons] Fetch UDB JSON...")
    UDB_JSON_URL = settings.UDB_JSON_URL
    UDB_API_TOKEN = settings.UDB_API_TOKEN
    logger.debug(f"Fetching data from {UDB_JSON_URL=}")

    if not UDB_JSON_URL:
        msg = "UDB integration is enabled but `UDB_JSON_URL` is not set. Check your `.env`."
        logger.error(msg)
        raise ValueError(msg)

    if UDB_API_TOKEN:
        # assume UDB API request if we have an API_TOKEN
        contract_fields = "person,contract_planned_checkin,contract_planned_checkout,contract_organization_unit,contract_contract_type,contract_organizational_positions"
        person_fields = "person_first_name,person_last_name,person_email_internal_business,person_email_private,id"
        url_request = urllib.request.Request(
            f"{UDB_JSON_URL}/api/external_interface/contracts/?contract-fields={contract_fields}&person-fields={person_fields}",
            headers={"X-API-KEY": UDB_API_TOKEN},
        )
    else:
        # use plain JSON_URL
        url_request = urllib.request.Request(UDB_JSON_URL)

    thumbnail_size = 400, 300
    person_images_dir = settings.MEDIA_DIR / settings.PERSON_IMAGE_UPLOAD_DIR
    person_images_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"{person_images_dir=}")

    # Fetch the data from the UDB server.
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
            "Check `UDB_JSON_URL` and network connectivity."
        )
        raise
    except TimeoutError:
        logger.error(f"UDB server at {url_request.full_url} did not respond within {UDB_REQUEST_TIMEOUT} seconds.")
        raise

    # Decode and parse the response.
    try:
        udb_obj = json.loads(data.decode("utf-8"))
        contracts = udb_obj["results"]["contracts"]
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

    for contract in contracts:
        udb_person_email_internal_business = contract["person"]["person_email_internal_business"]
        # udb_person_email_private = contract['person']['person_email_private']

        udb_person_uuid = contract["person"]["id"]
        udb_person_first_name = contract["person"]["person_first_name"]
        udb_person_last_name = contract["person"]["person_last_name"]
        udb_contract_planned_checkin = contract["contract_planned_checkin"]
        udb_contract_planned_checkout = contract["contract_planned_checkout"]
        udb_contract_organization_unit = (
            contract["contract_organization_unit"].get("name", "") if contract["contract_organization_unit"] else ""
        )
        udb_contract_contract_type = (
            contract["contract_contract_type"].get("name", "") if contract["contract_contract_type"] else ""
        )

        _positions = (
            contract["contract_organizational_positions"] if contract["contract_organizational_positions"] else ""
        )
        _positions = [p.get("name") for p in _positions]
        _positions = ", ".join(_positions)

        logger.debug(
            f"Processing UDB person uuid={udb_person_uuid}, last name={udb_person_last_name}, first name={udb_person_first_name}"
        )

        if udb_contract_organization_unit:
            udb_organizational_unit, _ = OrganizationalUnit.objects.get_or_create(name=udb_contract_organization_unit)

        udb_person_image_path_relative = ""
        try:
            udb_person_image = contract["person"]["person_image"]

            if udb_person_image:
                logger.debug(f"Converting image for {udb_person_uuid}...")
                udb_person_image_path_absolute = f"{person_images_dir}/{udb_person_uuid}.jpg"
                udb_person_image_path_relative = f"{settings.PERSON_IMAGE_UPLOAD_DIR}/{udb_person_uuid}.jpg"

                save_base64img_as_fileimg(
                    base64string=udb_person_image,
                    to_filepath=udb_person_image_path_absolute,
                    thumbnail_size=thumbnail_size,
                )

        except KeyError as key_error:
            logger.error(f"Failed setting image data: {key_error}")

        # TODO: Re-think matching/update logic
        try:
            # Match by email disabled for now, falling back to only
            # match against firstname and lastname combination.
            # match_by_email = udb_person_email_internal_business if udb_person_email_internal_business else udb_person_email_private

            defaults = dict(
                udb_person_uuid=udb_person_uuid,
                udb_person_first_name=udb_person_first_name,
                udb_person_last_name=udb_person_last_name,
                udb_person_email_internal_business=udb_person_email_internal_business,
                udb_contract_planned_checkin=udb_contract_planned_checkin,
                udb_contract_planned_checkout=udb_contract_planned_checkout,
                udb_contract_contract_type=udb_contract_contract_type,
                udb_contract_organization_unit=udb_contract_organization_unit,
                udb_contract_organizational_positions=_positions,
                udb_data_updated_at=now(),
                udb_person_image=udb_person_image_path_relative,
                organizational_unit=udb_organizational_unit,
                deleted_at=None,
                deleted_by=None,
            )

            person, created = Person.with_softdeleted_objects.update_or_create(
                # email=match_by_email,
                last_name=udb_person_last_name,
                first_name=udb_person_first_name,
                defaults=defaults,
            )

            if created:
                logger.debug(f"Person '{person}' created!")
            else:
                logger.debug(f"Person '{person}' updated!")

        except Person.DoesNotExist as does_not_exist_exception:
            logger.error(
                f"No dlcdb person found for udb email {udb_person_email_internal_business}: {does_not_exist_exception}"
            )
        except IntegrityError as integrity_error:
            logger.error(
                f"Integrity error for UDB: {udb_person_last_name}/{udb_person_first_name} - {integrity_error}. Hint: Does fist_name and last_name match? Names could have been updated in UDB."
            )
        except Exception as unknown_exception:
            # `person` may be unbound if the failure happened before
            # update_or_create() returned, so identify the record by its UDB data.
            logger.error(
                f"Failed to import UDB person uuid={udb_person_uuid} "
                f"({udb_person_last_name}/{udb_person_first_name}): {unknown_exception}"
            )
