# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Filters used by the device and record overviews.

Keeping these filters in the assets app makes the new frontend independent of
the Django admin's ``SimpleListFilter`` implementations.
"""

import django_filters
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Device, DeviceType, Inventory, Manufacturer, Record, Room, Supplier
from dlcdb.core.models.record import DEVICE_DISPOSITION_CHOICES


STATE_NO_RECORD = "no-record"
STATE_CHOICES = [(STATE_NO_RECORD, _("No active record")), *Record.RECORD_TYPE_CHOICES]

DUPLICATE_SERIAL = "serial_number"
DUPLICATE_NICKNAME = "nick_name"
DUPLICATE_CHOICES = [
    (DUPLICATE_SERIAL, _("Duplicate serial number")),
    (DUPLICATE_NICKNAME, _("Duplicate nickname")),
]


class DeviceFilter(django_filters.FilterSet):
    """Search and the high-value filters from the previous Device changelist."""

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    device_type = django_filters.ModelChoiceFilter(
        queryset=DeviceType.objects.all(),
        label=_("Type"),
        empty_label=_("Any device type..."),
    )
    state = django_filters.ChoiceFilter(
        method="state_filter",
        choices=STATE_CHOICES,
        label=_("State"),
        empty_label=_("Any state..."),
    )
    is_lentable = django_filters.ChoiceFilter(
        choices=[("true", _("Loanable")), ("false", _("Not loanable"))],
        method="lentable_filter",
        label=_("Loanable"),
        empty_label=_("Any loanability..."),
    )
    active_record__room = django_filters.ModelChoiceFilter(
        queryset=Room.objects.all(),
        label=_("Room"),
        empty_label=_("Any room..."),
    )
    manufacturer = django_filters.ModelChoiceFilter(
        queryset=Manufacturer.objects.all(),
        label=_("Manufacturer"),
        empty_label=_("Any manufacturer..."),
    )
    supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.all(),
        label=_("Supplier"),
        empty_label=_("Any supplier..."),
    )
    active_record__inventory = django_filters.ModelChoiceFilter(
        queryset=Inventory.objects.all(),
        label=_("Inventory"),
        empty_label=_("Any inventory..."),
    )
    is_imported = django_filters.ChoiceFilter(
        choices=[("true", _("Imported")), ("false", _("Not imported"))],
        method="imported_filter",
        label=_("Import"),
        empty_label=_("Any import status..."),
    )
    duplicate = django_filters.ChoiceFilter(
        method="duplicate_filter",
        choices=DUPLICATE_CHOICES,
        label=_("Duplicates"),
        empty_label=_("No duplicate filter..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("edv_id", "it_id"),
            ("sap_id", "inventory_id"),
            ("device_type__name", "type"),
            ("manufacturer__name", "manufacturer"),
            ("series", "model"),
            ("active_record__record_type", "state"),
            ("active_record__room__number", "room"),
            ("modified_at", "modified"),
            ("tenant__name", "tenant"),
        ),
        # Keyed by model field name, not by the exposed parameter. Without these,
        # django-filter derives the labels from the parameter: "It id", "Inventory id".
        field_labels={
            "edv_id": _("IT ID"),
            "sap_id": _("Inventory ID"),
        },
    )

    class Meta:
        model = Device
        fields = [
            "search",
            "device_type",
            "state",
            "is_lentable",
            "active_record__room",
            "manufacturer",
            "supplier",
            "active_record__inventory",
            "is_imported",
            "duplicate",
            "ordering",
        ]

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(edv_id__icontains=value)
            | Q(sap_id__icontains=value)
            | Q(serial_number__icontains=value)
            | Q(nick_name__icontains=value)
            | Q(device_type__name__icontains=value)
            | Q(manufacturer__name__icontains=value)
            | Q(series__icontains=value)
            | Q(order_number__icontains=value)
            | Q(active_record__person__first_name__icontains=value)
            | Q(active_record__person__last_name__icontains=value)
            | Q(active_record__person__email__icontains=value)
        )

    def state_filter(self, queryset, name, value):
        if value == STATE_NO_RECORD:
            return queryset.filter(active_record__isnull=True)
        if value:
            return queryset.filter(active_record__record_type=value)
        return queryset

    def lentable_filter(self, queryset, name, value):
        return queryset.filter(is_lentable=value == "true") if value else queryset

    def imported_filter(self, queryset, name, value):
        return queryset.filter(is_imported=value == "true") if value else queryset

    def duplicate_filter(self, queryset, name, value):
        if value not in {DUPLICATE_SERIAL, DUPLICATE_NICKNAME}:
            return queryset

        duplicates = (
            queryset.exclude(**{f"{value}__isnull": True})
            .exclude(**{value: ""})
            .order_by()
            .values(value)
            .annotate(count=Count("pk"))
            .filter(count__gt=1)
            .values(value)
        )
        return queryset.filter(**{f"{value}__in": duplicates})


class RecordFilter(django_filters.FilterSet):
    """Search and filters for the read-only record trail.

    Device and person are deliberately not dropdowns: both have far too many
    rows to render as options. They are reachable through ``search`` instead,
    and a single device is reachable as a page scope (``?device=``).
    """

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    record_type = django_filters.ChoiceFilter(
        choices=Record.RECORD_TYPE_CHOICES,
        label=_("Record type"),
        empty_label=_("Any record type..."),
    )
    # An explicit ChoiceFilter, not a BooleanFilter: the filterbar renders only
    # choice-ish filters, so a BooleanFilter would show up as no dropdown at all.
    is_active = django_filters.ChoiceFilter(
        choices=[("true", _("Current")), ("false", _("Superseded"))],
        method="active_filter",
        label=_("Validity"),
        empty_label=_("Current and superseded..."),
    )
    device__device_type = django_filters.ModelChoiceFilter(
        queryset=DeviceType.objects.all(),
        label=_("Device type"),
        empty_label=_("Any device type..."),
    )
    room = django_filters.ModelChoiceFilter(
        queryset=Room.objects.all(),
        label=_("Room"),
        empty_label=_("Any room..."),
    )
    inventory = django_filters.ModelChoiceFilter(
        queryset=Inventory.objects.all(),
        label=_("Inventory"),
        empty_label=_("Any inventory..."),
    )
    device__manufacturer = django_filters.ModelChoiceFilter(
        queryset=Manufacturer.objects.all(),
        label=_("Manufacturer"),
        empty_label=_("Any manufacturer..."),
    )
    disposition_state = django_filters.ChoiceFilter(
        choices=DEVICE_DISPOSITION_CHOICES,
        label=_("Whereabouts"),
        empty_label=_("Any whereabouts..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created"),
            ("record_type", "type"),
            ("device__edv_id", "device"),
            ("room__number", "room"),
            ("person__last_name", "person"),
            ("effective_until", "valid_until"),
        ),
        # Keyed by model field path, not by the exposed parameter — same reason
        # as DeviceFilter: otherwise the labels read "Created at", "Record type".
        field_labels={
            "created_at": _("Created"),
            "record_type": _("Record type"),
            "device__edv_id": _("Device"),
            "room__number": _("Room"),
            "person__last_name": _("Lender"),
            "effective_until": _("Valid until"),
        },
    )

    class Meta:
        model = Record
        fields = [
            "search",
            "record_type",
            "is_active",
            "device__device_type",
            "room",
            "inventory",
            "device__manufacturer",
            "disposition_state",
            "ordering",
        ]

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(device__edv_id__icontains=value)
            | Q(device__sap_id__icontains=value)
            | Q(device__serial_number__icontains=value)
            | Q(person__first_name__icontains=value)
            | Q(person__last_name__icontains=value)
            | Q(person__email__icontains=value)
            | Q(room__number__icontains=value)
            # The free-text fields are what make a trail searchable at all
            # ("why was this scrapped", "where did it go").
            | Q(note__icontains=value)
            | Q(removed_info__icontains=value)
        )

    def active_filter(self, queryset, name, value):
        return queryset.filter(is_active=value == "true") if value else queryset


class DeviceTypeFilter(django_filters.FilterSet):
    """Search and the has-note filter from the previous DeviceType changelist."""

    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    has_note = django_filters.ChoiceFilter(
        choices=[("has_note", _("Has note")), ("has_no_note", _("No note"))],
        method="note_filter",
        label=_("Note"),
        empty_label=_("Any note status..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("prefix", "prefix"),
            ("assets_count", "assets"),
        ),
    )

    class Meta:
        model = DeviceType
        fields = ["search", "has_note", "ordering"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(prefix__icontains=value))

    def note_filter(self, queryset, name, value):
        # Same semantics as the admin's HasNoteFilter.
        if value == "has_note":
            return queryset.exclude(note__exact="")
        if value == "has_no_note":
            return queryset.filter(note__exact="")
        return queryset


class ManufacturerFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    ordering = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("assets_count", "assets"),
        ),
    )

    class Meta:
        model = Manufacturer
        fields = ["search", "ordering"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(note__icontains=value))


class SupplierFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    ordering = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("assets_count", "assets"),
        ),
    )

    class Meta:
        model = Supplier
        fields = ["search", "ordering"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(note__icontains=value))
