# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Starter content for the editable :class:`~dlcdb.lending.models.LendingProfile` fields.

Both fields are plain ``TextField``s the user edits in the admin, but they should
not start out empty: an empty ``lent_sheet_template`` makes the print views fail
(see :class:`dlcdb.lending.loader.DatabaseLoader`). The shipped starter content
therefore lives in real files next to the other lending templates, and the
functions below are used as the fields' ``default``. Django serialises callable
defaults by import path, so the content never ends up inlined in a migration.

The values are only a starting point: they are copied into the database row when
a profile is created and are the user's to edit from then on. Editing the files
here does not change existing profiles.

Because migrations reference these functions by import path, their names and
location must stay stable.
"""

from pathlib import Path

_STARTER_DIR = Path(__file__).parent / "templates" / "lending"
_LENT_SHEET = _STARTER_DIR / "lent_sheet_starter.html"
_CHECKLIST = _STARTER_DIR / "lending_preparation_checklist_starter.txt"


def _read(path):
    """
    Return the shipped starter content, or an empty string if the file is
    unreadable. Both target fields are ``blank=True``, so an empty value is
    always legal and a missing file cannot break model instantiation.
    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def get_starter_lent_sheet_template():
    """Default for ``LendingProfile.lent_sheet_template``."""
    return _read(_LENT_SHEET)


def get_starter_lending_preparation_checklist():
    """Default for ``LendingProfile.lending_preparation_checklist``."""
    return _read(_CHECKLIST)
