# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Downloadable CSV template for the device import.
"""

import csv
from io import StringIO

from dlcdb.core.models import Record

from .models import ImporterList


# Two complete example rows so the template shows the expected value formats
# (dates as YYYY-MM-DD, booleans as yes/no): a notebook placed in a room and a
# smartphone that is currently lent. Both import cleanly as-is, which is
# guarded by a test.
EXAMPLE_ROWS = [
    {
        "SAP_ID": "1234567-0",
        "ROOM": "101",
        "EDV_ID": "NTB0001",
        "DEVICE_TYPE": "Notebook",
        "SERIAL_NUMBER": "SN-2026-0001",
        "MANUFACTURER": "Example Inc.",
        "SERIES": "ExampleBook 14",
        "SUPPLIER": "IT Supplies Ltd.",
        "PURCHASE_DATE": "2026-01-15",
        "WARRANTY_EXPIRATION_DATE": "2029-01-15",
        "CONTRACT_EXPIRATION_DATE": "2029-01-15",
        "COST_CENTRE": "4711",
        "BOOK_VALUE": "1499.00",
        "NOTE": "Example row - replace with real data",
        "MAC_ADDRESS": "00:11:22:33:44:55",
        "EXTRA_MAC_ADDRESSES": "00:11:22:33:44:56",
        "NICK_NAME": "notebook-01",
        "IS_LENTABLE": "yes",
        "IS_LICENCE": "no",
        "RECORD_TYPE": Record.INROOM,
        "RECORD_NOTE": "Initial import",
        "ORDER_NUMBER": "PO-2026-001",
    },
    {
        "SAP_ID": "1234567-1",
        "ROOM": "101",
        "EDV_ID": "SMA0001",
        "DEVICE_TYPE": "Smartphone",
        "SERIAL_NUMBER": "SN-2026-0002",
        "MANUFACTURER": "Example Inc.",
        "SERIES": "ExamplePhone 5",
        "SUPPLIER": "IT Supplies Ltd.",
        "PURCHASE_DATE": "2026-02-01",
        "WARRANTY_EXPIRATION_DATE": "2028-02-01",
        "COST_CENTRE": "4711",
        "BOOK_VALUE": "899.00",
        "NOTE": "Example row - replace with real data",
        "NICK_NAME": "smartphone-01",
        "IS_LENTABLE": "yes",
        "IS_LICENCE": "no",
        "RECORD_TYPE": Record.LENT,
        "RECORD_NOTE": "Example lending",
        "ORDER_NUMBER": "PO-2026-002",
        "LENDER_FIRST_NAME": "Ada",
        "LENDER_LAST_NAME": "Lovelace",
        "LENDER_EMAIL": "ada.lovelace@example.com",
        "LENDER_OU": "Mathematics",
        "LENT_START_DATE": "2026-03-01",
        "LENT_DESIRED_END_DATE": "2026-09-01",
        "LENT_NOTE": "Example loan",
        "LENT_REASON": "Home office",
        "LENT_ACCESSORIES": "Charger, case",
    },
]


def build_import_template_csv():
    """CSV import template: all columns plus the two example rows."""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ImporterList.VALID_COL_HEADERS, restval="")
    writer.writeheader()
    writer.writerows(EXAMPLE_ROWS)
    return buffer.getvalue()
