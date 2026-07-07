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
    title = "DLCDB Report: from {from_date} to {to_date} for {event} ({count})".format(
        from_date=window_start.date(),
        to_date=window_end.date(),
        event=event,
        count=records.count(),
    )

    # Spreadsheet titles must not exceed 31 characters.
    spreadsheet_title = "{event}_{from_date:%Y%m%d}-{to_date:%Y%m%d}".format(
        event=event,
        from_date=window_start.date(),
        to_date=window_end.date(),
    )

    text_rows = get_records_as_text(records=records, title=title, event=event, condition=condition)
    spreadsheet = get_records_as_spreadsheet(records=records, title=spreadsheet_title, event=event)
    filename = "{}_{}.xlsx".format(slugify(title), uuid.uuid1())

    return Report.objects.create(
        title=title,
        body=text_rows,
        spreadsheet=File(spreadsheet, name=filename),
    )
