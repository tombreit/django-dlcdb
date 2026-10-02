# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Device, DeviceType, Manufacturer, Record, Room, Supplier
from dlcdb.tenants.shortcuts import limit_tenant_field
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.widgets import DevicePickerMultiField, IconPickerWidget, TomSelectWidget


class RelocateForm(forms.Form):
    """
    Relocate form: move one or more devices to a single target room. ``devices``
    is the multi-select device picker (each chosen device contributes its own
    hidden input, see ``theme/js/picker.js``); ``new_room`` is a single-select
    picker. The form only validates that real devices and a non-deleted room were
    chosen.

    The caller passes ``device_queryset`` (tenant-scoped) so validation rejects a
    device pk from another tenant instead of relocating it. Assigning that
    queryset also re-wires the widget, so selected cards re-render after a
    validation error with no extra plumbing.
    """

    devices = DevicePickerMultiField(
        source="move",
        queryset=Device.objects.none(),
        placeholder=_("Search by EDV/Inv. no., manufacturer, serial…"),
        error_messages={"required": _("Please select at least one device to move.")},
    )
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.filter(deleted_at__isnull=True),
        widget=forms.HiddenInput,
        error_messages={"required": _("Please select a target room.")},
    )

    def __init__(self, *args, device_queryset=None, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        if device_queryset is not None:
            self.fields["devices"].queryset = device_queryset
        if request is not None:
            # Let the widget gate the selected card's admin link on the user's perm.
            self.fields["devices"].widget.user = request.user


class DeviceForm(forms.ModelForm):
    """The editable operational fields of a device.

    Audit, import and UUID values intentionally remain model data rather than
    form fields: they explain where a device came from, but are not ordinary
    operator input.
    """

    class Meta:
        model = Device
        fields = [
            "edv_id",
            "sap_id",
            "device_type",
            "is_lentable",
            "is_licence",
            "tenant",
            "manufacturer",
            "series",
            "serial_number",
            "note",
            "supplier",
            "order_number",
            "cost_centre",
            "purchase_date",
            "warranty_expiration_date",
            "contract_start_date",
            "contract_expiration_date",
            "contract_termination_date",
            "procurement_note",
            "contact_person_internal",
            "url",
            "nick_name",
            "mac_address",
            "extra_mac_addresses",
            "machine_encryption_key",
            "backup_encryption_key",
        ]
        widgets = {
            # FK selects over small reference tables that benefit from
            # type-to-filter. TomSelectWidget carries the searchable-select
            # contract; theme.js enhances it client-side (same mechanism the
            # licenses/lending/inventory apps use). The large Person relation is
            # handled separately by the HTMX live-search picker (see
            # contact_person_internal below).
            "device_type": TomSelectWidget(),
            "manufacturer": TomSelectWidget(),
            "supplier": TomSelectWidget(),
            # An <input type="date"> is ISO-only, whatever the locale; without
            # `format` it renders empty and saves empty (test_native_date_widgets).
            "purchase_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "warranty_expiration_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "contract_start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "contract_expiration_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "contract_termination_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
            "procurement_note": forms.Textarea(attrs={"rows": 3}),
            # Rendered as a hidden field driven by the live-search person picker
            # (theme/includes/_picker.html); a full <select> of every Person is
            # what made the detail page slow. Mirrors the admin autocomplete.
            "contact_person_internal": forms.HiddenInput(),
            "extra_mac_addresses": forms.Textarea(attrs={"rows": 2}),
            "machine_encryption_key": forms.Textarea(attrs={"rows": 3}),
            "backup_encryption_key": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)

        limit_tenant_field(self.fields["tenant"], request.tenants)

        add_bootstrap_classes(self)

    def clean_is_lentable(self):
        is_lentable = self.cleaned_data["is_lentable"]
        active_record = getattr(self.instance, "active_record", None)
        if (
            self.instance.pk
            and active_record
            and active_record.record_type == Record.LENT
            and is_lentable != self.instance.is_lentable
        ):
            raise ValidationError(_("Loanability cannot be changed while this device is lent."))
        return is_lentable


class DeviceTypeForm(forms.ModelForm):
    class Meta:
        model = DeviceType
        fields = ["name", "prefix", "icon", "note"]
        widgets = {
            "icon": IconPickerWidget(),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class ManufacturerForm(forms.ModelForm):
    class Meta:
        model = Manufacturer
        fields = ["name", "note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The model allows a NULL name (legacy data); a nameless manufacturer
        # renders as "None" everywhere, so the frontend requires one.
        self.fields["name"].required = True
        add_bootstrap_classes(self)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact", "note"]
        widgets = {
            "contact": forms.Textarea(attrs={"rows": 3}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Same reasoning as ManufacturerForm: no nameless suppliers.
        self.fields["name"].required = True
        add_bootstrap_classes(self)
