import csv
import os

from collections import namedtuple
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import formats

import segno

from .models import SapListComparisonResult


def uuid2qrcode(uuid, infix=None):
    qrcode = namedtuple("qrcode", ["filename", "fileobj"])

    uuid = str(uuid)  # Ensure uuid is a string and not an instance of UUID
    qr_text = '{prefix}{infix}{uuid}'.format(
        uuid=uuid,
        prefix=settings.QRCODE_PREFIX,
        infix=infix if infix else '',
    )
    qr_filename = '{0}.svg'.format(qr_text)
    qr_fileobj = segno.make(qr_text)

    _fileobj_io = BytesIO()
    qr_fileobj.save(_fileobj_io, "SVG")
    qr_fileobj = ContentFile(_fileobj_io.getvalue())

    return qrcode(qr_filename, qr_fileobj)


def get_devices_for_room(request, room_pk):
    from ..core.models import Device, Room

    # By default do not expose any devices
    devices_qs = Device.objects.none()

    room = Room.objects.get(pk=room_pk)
    base_qs = room.get_devices()

    if request.user.is_superuser:
        # No pre-filtering for superusers
        devices_qs = base_qs
    elif request.tenant:
        # Filter by tenant
        devices_qs = base_qs.filter(tenant=request.tenant)

    return devices_qs.order_by('-modified_at')


def unique_seq(sequence):
    """
    Eleminate duplicates in a list while preserving the order
    See: http://www.martinbroadhurst.com/removing-duplicates-from-a-list-while-preserving-order-in-python.html
    """
    seen = set()
    return [x for x in sequence if not (x in seen or seen.add(x))]


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
    :param sap_list_obj:
    :return:
    """

    # ensure that no objects are created if any exception occurs during
    # compare.
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
    Executes the compare logic.
    :param sap_list_obj:
    :return:
    """

    from dlcdb.core.models import Inventory, Device

    file_path = sap_list_obj.file.path
    new_rows = []
    current_inventory = Inventory.objects.filter(is_active=True).order_by('-created_at').first()

    device_sap_ids = list(Device.objects.values_list("sap_id", flat=True))
    device_sap_ids = list(filter(None, device_sap_ids))

    with open(file_path, 'r', encoding='utf-8') as f:

        rows = csv.DictReader(f, delimiter=",")

        for idx, row in enumerate(rows):
            # if rows.line_num < 7:
            #     continue
            
            new_row = row

            # sap_id = row['Anlage']
            # # if row['UNr.'] != '' and str(row['UNr.']).isdigit() and int(row['UNr.']) > 0:
            # # We use whatever we get as 'UNr.' (which could be zero)
            # if row['Unternummer']:
            #     sap_id += '-' + row['Unternummer']

            sap_id = get_match_for_sap_id(device_sap_ids, row['Anlage'], row['Unternummer'], return_type="device_sap_id")

            # print(80 * '=')
            # print(f"{type(sap_id)=}")
            # print(f"{sap_id=}")

            if sap_id:
                # get the device and query the corresponding active record.
                obj = Device.objects.get(sap_id=sap_id)
                record = obj.active_record
                if record:
                    # there is a record
                    new_row.update({'TYPE': record.get_record_type_display()})

                    # insert information about room changes since import
                    old_room = row['Raum']
                    new_room = ''
                    if record.room:
                        new_room = record.room.number

                    new_row.update({'OLD ROOM': old_room})
                    new_row.update({'NEW ROOM': new_room})
                    new_row.update({'ROOM NEQ': old_room != new_room})

                    # if obj was modified during inventory process
                    if record.inventory == current_inventory:
                        new_row.update({'CURRENT INVENTORY': current_inventory.name})
                    else:
                        new_row.update({'CURRENT INVENTORY': 'FALSE'})

                    new_row.update({'REC created_at': formats.date_format(record.created_at, "SHORT_DATETIME_FORMAT")})
                    new_row.update({'REC created by': record.username})
                else:
                    # there is no record for this device
                    new_row.update({'CURRENT RECORD?': 'NO CURRENT RECORD'})

                # finally append the notes for this inventory
                if current_inventory:
                    note_str = ''
                    for note in obj.device_notes.filter(inventory=current_inventory):
                        note_str += note.text + '***'
                    new_row.update({'NOTE': note_str})

            else:
                new_row.update({'IN_DLCDB?': 'NOT IN DLCDB'})

            new_rows.append(new_row)

    return new_rows
