# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Validation helpers for CSV device imports.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_column_headers(*, current_col_headers, expected_col_headers):
    current = set(current_col_headers or [])
    expected = set(expected_col_headers)
    missing = expected - current
    if missing:
        raise ValidationError(
            _(
                "The CSV file is missing required column headers. "
                "Missing column(s): %(missing)s. "
                "Expected all of: %(expected)s."
            ),
            code="missing_columns",
            params={
                "missing": ", ".join(sorted(missing)),
                "expected": ", ".join(sorted(expected)),
            },
        )
