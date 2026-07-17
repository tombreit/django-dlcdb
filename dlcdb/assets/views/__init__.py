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
from .masterdata import (
    device_type_add,
    device_type_detail,
    device_type_index,
    manufacturer_add,
    manufacturer_detail,
    manufacturer_index,
    supplier_add,
    supplier_detail,
    supplier_index,
)
from .relocate import relocate, room_search

__all__ = [
    "device_index",
    "device_add",
    "device_detail",
    "device_type_index",
    "device_type_add",
    "device_type_detail",
    "manufacturer_index",
    "manufacturer_add",
    "manufacturer_detail",
    "supplier_index",
    "supplier_add",
    "supplier_detail",
    "person_search",
    "relocate",
    "room_search",
]
