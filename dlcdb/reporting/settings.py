# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from ..core.models import Record


LENT_OVERDUE_TOLERANCE_DAYS = 5


# object: Record
EXPOSED_FIELDS = [
    # {
    #     'model': [],
    #     'field': 'pk',
    #     'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    # },
    {
        "model": [],
        "field": "record_type",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": [],
        "field": "created_at",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": [],
        "field": "username",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": ["device"],
        "field": "sap_id",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": ["device"],
        "field": "edv_id",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": ["device"],
        "field": "series",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": ["device"],
        "field": "serial_number",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": ["device", "manufacturer"],
        "field": "name",
        "used_for": [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        "model": ["room"],
        "field": "number",
        "used_for": [Record.INROOM],
    },
    {
        "model": ["person"],
        "field": "last_name",
        "used_for": [Record.LENT],
    },
    {
        "model": ["person"],
        "field": "first_name",
        "used_for": [Record.LENT],
    },
    {
        "model": ["person"],
        "field": "email",
        "used_for": [Record.LENT],
    },
    {
        "model": [],
        "field": "lent_desired_end_date",
        "used_for": [Record.LENT],
    },
    {
        "model": [],
        "field": "removed_date",
        "used_for": [Record.REMOVED],
    },
    {
        "model": [],
        "field": "removed_info",
        "used_for": [Record.REMOVED],
    },
]
