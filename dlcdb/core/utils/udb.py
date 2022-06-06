import json
import logging
from django.conf import settings
from django.utils.timezone import now
import urllib.request

from dlcdb.core.models import Person
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
            data = response.read()
            udb_obj = json.loads(data.decode('utf-8'))

            contracts = udb_obj['results']['contracts']

            for contract in contracts:
                print(80 * "-")

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

                    person, created = Person.objects.update_or_create(
                        email=match_by_email,
                        last_name=udb_person_last_name,
                        first_name=udb_person_first_name,
                        defaults=defaults,
                    )

                    if created:
                        print(f"Person {person} created!")
                    else:
                        print(f"Person {person} updated!")
    
                except Person.DoesNotExist as e:
                    print(f"No dlcdb person found for udb email {udb_person_email_internal_business}")
                except Exception as e:
                    print(80 * "x")
                    print(e)
                    print(f"{udb_person_last_name}, {udb_person_first_name}, {udb_person_email_internal_business}")
                else:
                    "Congrats: no exception!"

    except urllib.error.HTTPError as e:
        print(f"Ups, something went wrong: {e}")


def import_udb_person_images():
    logger.info("[huey person images utils: import_udb_person_images] Fetch UDB JSON...")
    UDB_JSON_URL = settings.UDB_JSON_PERSON_IMAGES_URL
    print(f"Fetching data from {UDB_JSON_URL=}")

    dlcdb_person = Person.objects.filter(udb_person_uuid__isnull=False)
    udb_person_images = {}
    
    with urllib.request.urlopen(UDB_JSON_URL) as response:
        data = response.read()
        udb_obj = json.loads(data.decode('utf-8'))
        contracts = udb_obj['results']['contracts']

        for contract in contracts:

            try:
                udb_person_last_name = contract['person']['person_last_name']
                person_image = contract['person']['person_image']
                print(udb_person_last_name, person_image)
            except KeyError as e:
                print(e)
            else:
                pass
                # person_uuid = contract['person']['id']
                # udb_person_images.update({person_uuid: person_image})

        #print(udb_person_images)
