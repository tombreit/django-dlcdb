import json
import logging
from operator import itemgetter
from tkinter import N
from django.conf import settings
from django.utils.timezone import now
from django.db import IntegrityError
import urllib.request

from dlcdb.core.models import Person, OrganizationalUnit
from .helpers import save_base64img_as_fileimg


logger = logging.getLogger(__name__)


def import_udb_persons():
    logger.info("[huey persons utils: import_udb_persons] Fetch UDB JSON...")
    UDB_JSON_URL = settings.UDB_JSON_URL
    print(f"Fetching data from {UDB_JSON_URL=}")

    thumbnail_size = 400, 300
    person_images_dir = settings.MEDIA_DIR / settings.PERSON_IMAGE_UPLOAD_DIR
    person_images_dir.mkdir(parents=True, exist_ok=True)
    print(f"{person_images_dir=}")

    dlcdb_persons = Person.objects.all()

    try:
        with urllib.request.urlopen(UDB_JSON_URL) as response:
            data = response.read().decode('utf-8')
            udb_obj = json.loads(data)

            contracts = udb_obj['results']['contracts']

            for contract in contracts:
                print(80 * "=")
                print(f"Processing person with UDB uuid = {contract['person']['id']}")

                udb_person_email_internal_business = contract['person']['person_email_internal_business']
                udb_person_email_private = contract['person']['person_email_private']

                udb_person_uuid = contract['person']['id']
                udb_person_first_name = contract['person']['person_first_name']
                udb_person_last_name = contract['person']['person_last_name']
                udb_contract_planned_checkin = contract['contract_planned_checkin']
                udb_contract_planned_checkout = contract['contract_planned_checkout']
                udb_contract_organization_unit = contract['contract_organization_unit'].get("name", "") if contract['contract_organization_unit'] else ""
                udb_contract_contract_type = contract['contract_contract_type'].get("name", "") if contract['contract_contract_type'] else ""

                _positions = contract['contract_organizational_positions'] if contract['contract_organizational_positions'] else ""
                _positions = [p.get("name") for p in _positions]
                _positions = ", ".join(_positions)

                if udb_contract_organization_unit:
                    udb_organizational_unit, _ = OrganizationalUnit.objects.get_or_create(name=udb_contract_organization_unit)

                try:
                    udb_person_image = contract['person']['person_image']
                    udb_person_image_path_relative = ""

                    if udb_person_image:
                        print(f"Converting image for {udb_person_uuid}...")
                        udb_person_image_path_absolute = f"{person_images_dir}/{udb_person_uuid}.jpg"
                        udb_person_image_path_relative = f"{settings.PERSON_IMAGE_UPLOAD_DIR}/{udb_person_uuid}.jpg"

                        save_base64img_as_fileimg(
                            base64string=udb_person_image,
                            to_filepath=udb_person_image_path_absolute,
                            thumbnail_size=thumbnail_size,
                        )

                except KeyError as e:
                    print(f"{e}")

                # TODO: Re-think matching/update logic
                try:
                    match_by_email = udb_person_email_internal_business if udb_person_email_internal_business else udb_person_email_private

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
                    )

                    print(f"Search for match for:")
                    print(f"{match_by_email=}")
                    print(f"{udb_person_last_name=}")
                    print(f"{udb_person_first_name=}")

                    person, created = Person.with_softdeleted_objects.update_or_create(
                        email=match_by_email,
                        last_name=udb_person_last_name,
                        first_name=udb_person_first_name,
                        defaults=defaults,
                    )

                    _postponed_save_person = False

                    if created:
                        print(f"Person '{person}' created!")
                    else:
                        print(f"Person '{person}' updated!")

                        # In case the matched person was soft delted, re-activate
                        # that person. 
                        # ToDo: Check if a history log entry gets created.
                        if person.deleted_at:
                            person.deleted_at = None
                            person.deleted_by = None
                            _postponed_save_person = True

                    if all([
                        udb_organizational_unit,
                        udb_organizational_unit != person.organizational_unit
                    ]):
                        print(f"'{person}' OU '{person.organizational_unit}' updated to '{udb_organizational_unit}'!")
                        person.organizational_unit = udb_organizational_unit
                        _postponed_save_person = True

                    if _postponed_save_person:
                        person.save()
    
                except Person.DoesNotExist as does_not_exist_exception:
                    print(f"No dlcdb person found for udb email {udb_person_email_internal_business}: {does_not_exist_exception}")
                except IntegrityError as integrity_error:
                    print(
                        f"Integrity error for:\n"
                        f"DLCDB: {person.last_name}/{person.first_name}/{person.email}\n"
                        f"UDB: {udb_person_last_name}/{udb_person_first_name}/{match_by_email}\n"
                        f"{integrity_error}"
                    )
                except Exception as unknown_exception:
                    print(f"Todo: Catch via more specific exception: for '{person}' {unknown_exception}")
                    print(f"{udb_person_last_name}, {udb_person_first_name}, {udb_person_email_internal_business}")

    except urllib.error.HTTPError as http_error:
        print(f"Ups, something went wrong fetching {UDB_JSON_URL}: {http_error}")
