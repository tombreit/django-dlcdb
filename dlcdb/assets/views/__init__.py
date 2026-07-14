# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Public view callables for the assets app.

``views.py`` grew into a package as the app took on the standalone Device
frontend. Each module owns one view area; this file re-exports their public
callables so ``urls.py`` (``from . import views``) keeps working unchanged.
"""

from .devices import device_add, device_detail, device_index, person_search
from .relocate import relocate, room_search

__all__ = [
    "device_index",
    "device_add",
    "device_detail",
    "person_search",
    "relocate",
    "room_search",
]
