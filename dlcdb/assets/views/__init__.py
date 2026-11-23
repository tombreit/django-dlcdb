# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Public view callables for the assets app.

``views.py`` grew into a package as the app took on the standalone Device
frontend. Each module owns one view area; this file re-exports their public
callables so ``urls.py`` (``from . import views``) keeps working unchanged.
"""

from .devices import (
    device_add,
    device_detail,
    device_export_csv,
    device_history,
    device_index,
    device_order,
    device_transition,
    person_search,
)
from .masterdata import DeviceTypeViewSet, ManufacturerViewSet, SupplierViewSet
from .records import record_attachments, record_detail, record_index
from .relocate import relocate, room_search

__all__ = [
    "DeviceTypeViewSet",
    "ManufacturerViewSet",
    "SupplierViewSet",
    "device_add",
    "device_detail",
    "device_export_csv",
    "device_history",
    "device_index",
    "device_order",
    "device_transition",
    "person_search",
    "record_attachments",
    "record_detail",
    "record_index",
    "relocate",
    "room_search",
]
