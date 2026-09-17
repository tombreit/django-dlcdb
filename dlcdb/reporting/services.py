# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Public API of the reporting app: build report artifacts (title, text rows,
xlsx spreadsheet) for a set of records.

This module must not import from dlcdb.notifications - the notifications app
builds on reporting, not the other way around.
"""

import uuid

from django.core.files import File
from django.utils.text import slugify

from .models import Report
from .utils.representations import get_records_as_spreadsheet, get_records_as_text


def create_report(*, records, event, condition="", window_start, window_end) -> Report:
    """
    Create and persist a Report for the given records, covering the time
    window [window_start, window_end].
    """
    title = f"DLCDB Report: from {window_start.date()} to {window_end.date()} for {event} ({records.count()})"

    # Spreadsheet titles must not exceed 31 characters.
    spreadsheet_title = f"{event}_{window_start.date():%Y%m%d}-{window_end.date():%Y%m%d}"

    text_rows = get_records_as_text(records=records, title=title, event=event, condition=condition)
    spreadsheet = get_records_as_spreadsheet(records=records, title=spreadsheet_title, event=event)
    filename = f"{slugify(title)}_{uuid.uuid1()}.xlsx"

    return Report.objects.create(
        title=title,
        body=text_rows,
        spreadsheet=File(spreadsheet, name=filename),
    )
