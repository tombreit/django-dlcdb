# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import re
import csv
import codecs
from io import StringIO
from datetime import datetime


SAP_COL_UNTERNUMMER_KEYS = ["Unternummer", "UNr."]

SAP_COL_ADD = [
    "TENANT",
    "RECORD_TYPE",
    "SAP_ID",
    "EDV_ID",
    "SERIES",
    "WARRANTY_EXPIRATION_DATE",
    "IS_LENTABLE",
    "DEVICE_TYPE",
    "MAINTENANCE_CONTRACT_EXPIRATION_DATE",
    "RECORD_NOTE",
    "REMOVED_DATE",
    "NOTE",
    "NICK_NAME",
    "EXTRA_MAC_ADDRESSES",
    "PERSON",
    "SUPPLIER",
    "IS_LICENCE",
    "MAC_ADDRESS",
    "ORDER_NUMBER",
]

SAP_COL_MAP = {
    # Directly mappable cells:
    # "Anlagenbezeichnung": "SERIES",  # we fill edv_id with Anlagebezeichnung
    "SerialNr": "SERIAL_NUMBER",
    "Serialnummer": "SERIAL_NUMBER",
    "Hersteller": "MANUFACTURER",
    "Hersteller der Anlage": "MANUFACTURER",
    "Raum": "ROOM",
    "AnschWert": "BOOK_VALUE",
    "Kostenst.": "COST_CENTRE",
    "Kostenstelle": "COST_CENTRE",
    "Aktivdatum": "PURCHASE_DATE",
    "Aktivierung am": "PURCHASE_DATE",
    "Deakt.Dat.": "DEACTIVATED_DATE",
    "Deaktivierung am": "DEACTIVATED_DATE",
    # # Cells needing preprocessing:
    # "Anlage": "",
    # "UNr.": "",
    # "Anlagenbezeichnung"
    # # Currently ignored cells:
    # "Zujr": "",
    # "kumul AfA": "",
    # "Buchwert": "",
    # "Währg": "",
    # "BuKr": "",
    # "Deakt.Dat.": "",
    # "Kreditor": "",
    # "PSP-Element": "",
}

csv.register_dialect(
    "cleaned_dialect",
    skipinitialspace=True,
    delimiter=",",
    strict=True,
)


def get_iso_datestr(datestr):
    """
    Converts a german date string (31.12.2020) to an ISO date string (2020-12-31).
    """
    dateformat = "%d.%m.%Y"
    dateobj = datetime.strptime(datestr, dateformat)
    return f"{dateobj:%Y-%m-%d}"


def fix_room_notation(room: str) -> str:
    room = str(room)
    room = room.strip()

    try:
        pattern = re.compile(r"^(\d{1,2})$")
        room = pattern.match(room).group(1)
        room = f"{room:0>3}"
    except Exception:
        pass

    return room


def guess_record_type(*, room, deactivated_date):
    """
    If an asset has a deactivated_date, it was already decommissionend
    at that date and gets a REMOVED. Else an INROOM record.
    """
    from dlcdb.core.models import Record

    record_type = _room = _removed_date = None

    if deactivated_date:
        record_type = Record.REMOVED
        _removed_date = get_iso_datestr(deactivated_date)
    elif room:
        record_type = Record.INROOM
        _room = room

    return record_type, _room, _removed_date


def guess_device_type(description, tenant=None):
    """
    Tries to extract a device_type instance from a SAP description
    field.
    TODO: Use Tenant-aware device types.
    """
    description = description.lower()
    guessed_device_type = "Sonstiges (Verwaltung)"

    SAP_DEVICE_TYPES_MAP = {
        "Tisch": [],
        "Stuhl": ["Stühle", "Stuehle"],
        "Drehstuhl": ["Drehstühle", "Drehstuehle"],
        "Hocker": [],
        "Lampe/Leuchte": [],
        "Schrank": ["Schränke", "Schraenke"],
        "Regal": [],
        "Aktenvernichter": [],
        "Bücherwagen": ["Buecherwagen", "Bücherwägen", "Buecherwaegen"],
        "Container": [],
        "Bücher/Zeitschriften": ["Buch", "Buecher", "Zeitschriften", "Zeitschrift"],
        "Stellwand": [],
        "Bett": [],
        "Sonstiges (Verwaltung)": [],
    }

    for type_key, type_aliases in SAP_DEVICE_TYPES_MAP.items():
        if type_key.lower() in description:
            # print(f"*** -> {type_key} or IN {description}!")
            guessed_device_type = type_key
        elif any([alias.lower() in description for alias in type_aliases]):
            # print(f"*** -> alias IN {description}!")
            guessed_device_type = type_key

    return guessed_device_type


# def cleanup_sap_csv(file):
#     """
#     Process the SAP CSV file to clean it up:
#     Remove empty rows, leading non-data rows etc.

#     SAP is able to export to Excel, but in a weird format. We do not
#     handle Excel files for now, so these files have to be converted to
#     plain CSV manually (keeping the weird format intact).

#     Example:
#     row=b'"13.02.2023                                                                                  Dynamische Listenausgabe                                                                                          1",,,,,,,,,,,,,,,,,,,,,,,\n'
#     row=b',,,,,,,,,,,,,,,,,,,,,,,\n'
#     row=b'"     Berichtsdatum:",,,,31.12.2023,,"Anlagenbestand (aktueller Buchwert) - 01 Handelsrecht",,,,,,,,,,,,,,,,,\n'
#     row=b'"  Erstellungsdatum:",,,,13.02.2023,,,,,,,,,,,,,,,,,,,1\n'
#     row=b',,,,,,,,,,,,,,,,,,,,,,,\n'
#     row=b'"Buchungskreis",,,,,"GeschBereich",,"Bilanzposition","BestandskontoAHK",,,"Anlagenklasse",,,,,,,,,,,,\n'
#     row=b'"STRA",,,,,,,1010101000,2812913,,,2812913,,,,,,,,,,,,\n'
#     row=b',,,,,,,,,,,,,,,,,,,,,,,\n'
#     row=b',"Anlage","UNr.","Anlagenbezeichnung",,,,,"Aktivdatum","Zujr","      AnschWert",,"      kumul AfA","       Buchwert","W\xc3\xa4hrg","BuKr","Deakt.Dat.","Raum","Kreditor","Kostenst.","PSP-Element","SerialNr","Hersteller",\n'
#     row=b',,,,,,,,,,,,,,,,,,,,,,,\n'
#     row=b',6000224,0,"Microsoft Office 365 E3 Lizenz Annual",,,,,05.10.2022,2022,435,,-435,0,"EUR","STRA",,,800133,"K5300",,,,\n'

#     Basically we
#     * search the first row which seems to be the column headers
#     * strip all rows above
#     * convert the column header names to our own defined column headers
#     * check if the next row is empty, if so, delete that empty row
#     * return the cleaned CSV result file

#     2023-06-16:
#     SAP *does* export a simple Excel file if the right
#     buttons are used, so this function is not needed anymore
#     """

#     cleaned_buffer = StringIO()
#     _cleaned_writer = csv.writer(cleaned_buffer, dialect='cleaned_dialect')

#     rows = csv.reader(codecs.iterdecode(file, 'utf-8'))
#     for index, row in enumerate(rows):
#         # Remove leading and trailing whitespace
#         row = [cell.strip() for cell in row]

#         if index <= 7:
#             continue
#         elif not any(row):
#             continue
#         elif set(SAP_COL_MAP.keys()).issubset(row):
#             # This should be the header row
#             row = [SAP_COL_MAP.get(cell, cell) for cell in row]
#             row.extend(SAP_COL_ADD)  # Add obligatory column headers not present in import file
#         _cleaned_writer.writerow(row)

#     cleaned_buffer.seek(0)
#     return cleaned_buffer


def fill_col_headers(file):
    cleaned_buffer = StringIO()
    _cleaned_writer = csv.writer(cleaned_buffer, dialect="cleaned_dialect")

    rows = csv.reader(codecs.iterdecode(file, "utf-8"))
    for index, row in enumerate(rows):
        # Remove leading and trailing whitespace
        row = [cell.strip() for cell in row]

        # if set(SAP_COL_MAP.keys()).issubset(row):
        if index == 0:
            # This should be the header row
            row = [SAP_COL_MAP.get(cell, cell) for cell in row]
            row.extend(SAP_COL_ADD)  # Add obligatory column headers not present in import file
        _cleaned_writer.writerow(row)

    cleaned_buffer.seek(0)
    return cleaned_buffer


def adapt_cleaned_csv(file, tenant):
    """
    Modify SAP data to fit our schema.
    TODO/Idea: Use EDV_ID for the complete SAP description, with an counter
    added to be unique.
    """

    reader = csv.DictReader(file, dialect="cleaned_dialect")
    fieldnames = reader.fieldnames

    adapted_buffer = StringIO()
    _adapted_writer = csv.DictWriter(adapted_buffer, fieldnames=fieldnames, dialect="cleaned_dialect")

    _adapted_writer.writeheader()
    for index, row in enumerate(reader):
        room = fix_room_notation(row["ROOM"])

        record_type, _room, _removed_date = guess_record_type(
            room=room,
            deactivated_date=row["DEACTIVATED_DATE"],
        )

        # In some SAP export files the column is named 'Unternummer', in some
        # others 'UNr.':
        _unternummer = None

        for unternummer_key in SAP_COL_UNTERNUMMER_KEYS:
            try:
                _unternummer = row[unternummer_key]
            except KeyError:
                pass

        if not _unternummer:
            raise KeyError("Keine Unternummer (keine Spalte 'Unternummer' oder 'UNr.') gefunden!")

        sap_id = f"{row['Anlage']}-{_unternummer}"
        # We use the SAP asset description as the edv_id and prepend a
        # unique identifier (here: sap_id)
        edv_id = f"{row['Anlagenbezeichnung']} ({sap_id})"

        row["SAP_ID"] = sap_id
        row["EDV_ID"] = edv_id
        row["PURCHASE_DATE"] = get_iso_datestr(row["PURCHASE_DATE"])
        row["TENANT"] = tenant.name
        row["DEVICE_TYPE"] = guess_device_type(edv_id)  # Was: row['Anlagenbezeichnung']
        row["RECORD_TYPE"] = record_type
        row["ROOM"] = room
        row["REMOVED_DATE"] = _removed_date
        _adapted_writer.writerow(row)

    adapted_buffer.seek(0)
    return adapted_buffer


def convert_to_csv(csv_data):
    # Create a DictReader instance from the CSV data
    reader = csv.DictReader(csv_data, dialect="cleaned_dialect")
    fieldnames = reader.fieldnames

    # Convert the reader to a list of dictionaries
    data = list(reader)

    # Write the data to a StringIO buffer as a CSV
    csv_obj = StringIO()
    writer = csv.DictWriter(csv_obj, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)

    csv_obj.seek(0)
    return csv_obj


def convert_raw_sap_export(sap_csvfile, tenant, valid_col_headers):
    # cleaned_csv = cleanup_sap_csv(sap_csvfile)
    filled_headers_csv = fill_col_headers(sap_csvfile)
    adapted_csv = adapt_cleaned_csv(filled_headers_csv, tenant)
    final_csv = convert_to_csv(adapted_csv)

    return final_csv
