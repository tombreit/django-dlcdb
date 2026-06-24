# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

# Re-exported from the shared implementation in core.utils so the HTMX guard has
# a single source of truth (see dlcdb.core.utils.htmx).
from dlcdb.core.utils.htmx import htmx_permission_required

__all__ = ["htmx_permission_required"]
