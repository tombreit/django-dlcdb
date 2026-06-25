# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Device relocation for the frontend.

Feature-named module (rather than a generic ``services.py``) so further device
workflows get their own sibling modules (e.g. ``decommission.py``) instead of a
catch-all bucket.

The actual relocation logic lives in ``dlcdb.core.utils.relocate`` so the admin
bulk action and this frontend view share one implementation; this module just
re-exports it for local callers.
"""

from dlcdb.core.utils.relocate import RelocateResult, relocate_device

__all__ = ["RelocateResult", "relocate_device"]
