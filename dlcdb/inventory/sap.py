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

        for idx, row in enumerate(rows):
            new_row = row
            sap_id = get_match_for_sap_id(device_sap_ids, row['Anlage'], row['Unternummer'], return_type="device_sap_id")

            # print(80 * '=')
            # print(f"{type(sap_id)=}")
            # print(f"{sap_id=}")

            if sap_id:
                obj = Device.objects.get(sap_id=sap_id)
                active_record = obj.active_record
                inventorized_record = obj.get_current_inventory_record

                if inventorized_record:
                    record_inventory = inventorized_record.inventory.name
                    if record_inventory != current_inventory.name:
                        raise ValidationError(f"{record_inventory=} does not match {current_inventory.name=}. Exit!")

                    new_room = inventorized_record.room.number if inventorized_record.room else ""
                    record_type = inventorized_record.get_record_type_display()
                    record_created_at = formats.date_format(inventorized_record.created_at, "SHORT_DATETIME_FORMAT")
                    record_created_by = inventorized_record.username

                elif active_record:
                    record_inventory = 'FALSE'
                    new_room = active_record.room.number if active_record.room else ""
                    record_type = active_record.get_record_type_display()
                    record_created_at = formats.date_format(active_record.created_at, "SHORT_DATETIME_FORMAT")
                    record_created_by = active_record.username

                else:
                    # there is no record for this device
                    new_row.update({'CURRENT RECORD?': 'NO RECORD'})

                if inventorized_record or active_record:
                    old_room = row['Raum']

                    new_row.update({'CURRENT INVENTORY': record_inventory})
                    new_row.update({'TYPE': record_type})
                    new_row.update({'OLD ROOM': old_room})

                    new_row.update({'NEW ROOM': new_room})
                    new_row.update({'ROOM NEQ': old_room != new_room})
                    new_row.update({'REC CREATED_AT': record_created_at})
                    new_row.update({'REC CREATED BY': record_created_by})

            else:
                # SAP-ID not found in DLDB
                new_row.update({'IN_DLCDB?': 'NOT IN DLCDB'})

            # Append inventory notes for this device
            # A DLCDB inventory note could exists even if the given device does not
            # exist in the SAP file.
            if current_inventory:
                note_str = ''
                for note in obj.device_notes.filter(inventory=current_inventory):
                    note_str += note.text + '***'
                new_row.update({'NOTE': note_str})

            new_rows.append(new_row)

    return new_rows
