import json
import logging
from django.conf import settings
from django.utils.timezone import now
import urllib.request

from dlcdb.core.models import Person


logger = logging.getLogger(__name__)


# TODO: make this JSON_URL configurable
JSON_URL = "https://static.csl.mpg.de/udb2_dlcdbpersons/udb2_dlcdbpersons.json"
# JSON_URL = "file://{}/temp/udb2_dlcdbpersons.json".format(settings.BASE_DIR)

# print(f"{settings.BASE_DIR=}")


def import_udb_persons():
    logger.info("[huey persons utils: import_udb_persons] Fetch UDB JSON...")
    print(f"Fetching data from {JSON_URL=}")

    dlcdb_persons = Person.objects.all()

    with urllib.request.urlopen(JSON_URL) as response:
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

