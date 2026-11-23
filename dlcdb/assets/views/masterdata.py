# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The device master data: device types, manufacturers and suppliers, each a
ModelViewSet (theme/viewsets.py). Global, like the lending profiles: no tenant
scoping. No delete page: deleting and deactivating master data stays with the
superusers in the admin (DeviceType is soft-deleted, its delete() would bypass
PROTECT).
"""

from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import DeviceType, Manufacturer, Supplier
from dlcdb.theme.viewsets import Column, ModelViewSet, Usage

from ..filters import DeviceTypeFilter
from ..forms import DeviceTypeForm, ManufacturerForm, SupplierForm

NAME_WITH_NOTE = "theme/viewsets/cells/_name_with_note.html"

# Named "assets": the dashboard links the device types sorted by it.
ASSETS_COLUMN = Column(
    "assets",
    _("Assets"),
    sort_key="assets",
    classname="text-end",
    cell_template_name="theme/viewsets/cells/_count.html",
)


def _devices_usage(device_filter):
    """The edit page's card: the devices, linked to the device list filtered by the entry."""
    return Usage(_("Devices"), "assets", "assets:device_index", device_filter, "core.view_device", icon="bi-pc-display")


class MasterdataViewSet(ModelViewSet):
    """What the three share: the devices count and no delete page."""

    ordering = "name"
    delete_view_class = None

    def get_queryset(self):
        return self.model.objects.annotate(assets=Count("device", distinct=True))


class DeviceTypeViewSet(MasterdataViewSet):
    model = DeviceType
    form_class = DeviceTypeForm
    icon = "bi-palette"
    url_namespace = "device_type"
    usage = _devices_usage("device_type")
    list_display = [
        Column("name", _("Name"), sort_key="name", cell_template_name="assets/cells/_device_type_name.html"),
        Column(
            "prefix",
            _("Prefix"),
            sort_key="prefix",
            classname="d-none d-md-table-cell",
            cell_template_name="assets/cells/_code.html",
        ),
        ASSETS_COLUMN,
    ]
    filterset_class = DeviceTypeFilter
    search_fields = ["name", "prefix"]
    search_placeholder = _("Search name, prefix...")


class ManufacturerViewSet(MasterdataViewSet):
    model = Manufacturer
    form_class = ManufacturerForm
    icon = "bi-building"
    url_namespace = "manufacturer"
    usage = _devices_usage("manufacturer")
    list_display = [Column("name", _("Name"), sort_key="name", cell_template_name=NAME_WITH_NOTE), ASSETS_COLUMN]
    search_fields = ["name", "note"]
    search_placeholder = _("Search name, note...")


class SupplierViewSet(MasterdataViewSet):
    model = Supplier
    form_class = SupplierForm
    icon = "bi-truck"
    url_namespace = "supplier"
    usage = _devices_usage("supplier")
    list_display = [
        Column("name", _("Name"), sort_key="name", cell_template_name=NAME_WITH_NOTE),
        Column(
            "contact", _("Contact"), classname="d-none d-md-table-cell", cell_template_name="assets/cells/_contact.html"
        ),
        ASSETS_COLUMN,
    ]
    search_fields = ["name", "note"]
    search_placeholder = _("Search name, note...")
