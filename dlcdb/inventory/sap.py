import csv
import os

from django.conf import settings
from django.db import transaction
from django.utils import formats
from django.core.exceptions import ValidationError

from .utils import unique_seq


def get_match_for_sap_id(sap_ids, sap_anlagennummer, sap_anlagenunternummer=None, return_type=None):
    """
    Return_type: None (message) or "device_sap_id"
    Note: This should not be needed any more, since we should now only have valid
    and complete SAP IDs in our system. Notation: `Hauptnummer-Unternummer`.
    """
    match_msg = "0"
    matched_device_sap_id = None

    anlagennummer = sap_anlagennummer.strip()
    anlagenunternummer = sap_anlagenunternummer.strip()

    sap_id_exact = f"{anlagennummer}-{anlagenunternummer}"
    sap_id_combined = f"{anlagennummer}{anlagenunternummer}"
    sap_id_anlagennummeronly = f"{anlagennummer}"

    if sap_id_exact in sap_ids:
        match_msg = f"exact ({sap_id_exact})"
        matched_device_sap_id = sap_id_exact
    elif sap_id_combined in sap_ids:
        match_msg = f"combined ({sap_id_combined} vs. {anlagennummer}/{anlagenunternummer})"
        matched_device_sap_id = sap_id_combined
    elif sap_id_anlagennummeronly in sap_ids:
        match_msg = f"anlagenummeronly ({sap_id_anlagennummeronly} vs. {anlagennummer}/{anlagenunternummer})"
        matched_device_sap_id = sap_id_anlagennummeronly

    # print(80 * '~')
    # print(f"{match_msg=}")
    # print(f"{matched_device_sap_id=}")
    # print(f"{type(matched_device_sap_id)=}")

    return matched_device_sap_id if return_type == "device_sap_id" else match_msg


def create_sap_list_comparison(sap_list_obj):
    """
    Creates a SapListComparisonResult. Calls compare for the actual compare logic.
    """

    from .models import SapListComparisonResult

    # Ensure that no objects are created if any exception occurs during compare:
    with transaction.atomic():

        # the result as list of lists
        result_rows = compare_sap(sap_list_obj)

        comparison = SapListComparisonResult(
            sap_list=sap_list_obj,
        )
        comparison.save()

        original_name = sap_list_obj.file.name.split('/')[-1]
        file_name = 'result_{id}_{org_name}'.format(id=comparison.id, org_name=original_name)
        file_path = os.path.join(settings.MEDIA_ROOT, settings.SAP_LIST_COMPARISON_RESULT_FOLDER, file_name)

        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w", encoding='utf-16') as new_file:
            fieldnames = list(k for d in result_rows for k in d)
            fieldnames = unique_seq(fieldnames)

            writer = csv.DictWriter(
                new_file,
                fieldnames=fieldnames,
                dialect='excel-tab',
                # delimiter=';',
                # quotechar='"',
                quoting=csv.QUOTE_ALL,
                extrasaction='raise',
            )

            writer.writeheader()
            for row in result_rows:
                writer.writerow(row)

            comparison.file_name = file_name
            comparison.save()


def compare_sap(sap_list_obj):
    """
    Compare the current state of the DLCDB with an Excel spreadsheet:
    Search the DLCDB for SAP_IDs listet in the spreadsheet, enrich the
    information (row) of the given SAP_ID in the spreadsheet (basically)
    appending columns).
    """
    from dlcdb.core.models import Inventory, Device

    file_path = sap_list_obj.file.path
    current_inventory = Inventory.objects.get(is_active=True)

    device_sap_ids = list(Device.objects.values_list("sap_id", flat=True))
    device_sap_ids = list(filter(None, device_sap_ids))

    new_rows = []

    with open(file_path, 'r', encoding='utf-8') as f:
        rows = csv.DictReader(f, delimiter=",")

        for row in rows:
            new_row = row
            sap_id = get_match_for_sap_id(device_sap_ids, row['Anlage'], row['Unternummer'], return_type="device_sap_id")

            if sap_id:
                obj = Device.objects.get(sap_id=sap_id)
                active_record = obj.active_record
                inventorized_record = obj.get_current_inventory_record

                if inventorized_record:
                    if inventorized_record.inventory.name != current_inventory.name:
                        raise ValidationError(f"{inventorized_record.inventory.name=} does not match {current_inventory.name=}. Exit!")

                # Defaults
                record_for_sap = None
                record_inventory = 'FALSE'

                # Find the record to be listed in sap comparison
                if inventorized_record and active_record and inventorized_record.id < active_record.id:
                    # This device has an inventorized record but newer records
                    # exist so we pick the newest (active) record for sap
                    # compare sheet.
                    record_for_sap = active_record
                    record_inventory = inventorized_record.inventory.name
                elif inventorized_record and active_record:
                    # The inventorized record is the active record, no newer
                    # records exist
                    record_for_sap = inventorized_record
                    record_inventory = inventorized_record.inventory.name
                elif active_record and not inventorized_record:
                    # This device has no inventorized record but an active
                    # record.
                    record_for_sap = active_record

                # Finally set data for sap comparison csv file
                if record_for_sap:
                    old_room = row['Raum']
                    new_room = record_for_sap.room.number if record_for_sap.room else ""

                    new_row.update({
                        'CURRENT INVENTORY': record_inventory,
                        'TYPE': record_for_sap.get_record_type_display(),
                        'OLD ROOM': old_room,
                        'NEW ROOM': new_room,
                        'ROOM NEQ': old_room != new_room,
                        'REC CREATED_AT': formats.date_format(record_for_sap.created_at, "SHORT_DATETIME_FORMAT"),
                        'REC CREATED BY': record_for_sap.username,
                    })
                else:
                    # there is no record for this device
                    new_row.update({'CURRENT RECORD?': 'NO RECORD'})

            else:
                # SAP-ID not found in DLDB
                new_row.update({'IN_DLCDB?': 'NOT IN DLCDB'})

            # Append inventory notes for this device
            # A DLCDB inventory note could exists even if the given device does not
            # exist in the SAP file.
            if current_inventory:
                notes = obj.device_notes.filter(inventory=current_inventory)
                new_row.update({'NOTE': "; ".join(notes)})

            new_rows.append(new_row)

    return new_rows
