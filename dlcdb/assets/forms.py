# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Device, Record, Room
from dlcdb.theme.widgets import DevicePickerMultiField


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

    # FK selects over small reference tables that benefit from type-to-filter.
    # `is-tom-select` is enhanced client-side by theme.js (same mechanism the
    # licenses app uses). The large Person relation is handled separately by the
    # HTMX live-search picker (see contact_person_internal below).
    SEARCHABLE_SELECT_FIELDS = {"manufacturer", "device_type", "supplier"}

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
            "nick_name",
            "mac_address",
            "extra_mac_addresses",
            "machine_encryption_key",
            "backup_encryption_key",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "warranty_expiration_date": forms.DateInput(attrs={"type": "date"}),
            "contract_start_date": forms.DateInput(attrs={"type": "date"}),
            "contract_expiration_date": forms.DateInput(attrs={"type": "date"}),
            "contract_termination_date": forms.DateInput(attrs={"type": "date"}),
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
        self.request = request

        if not request.user.is_superuser:
            self.fields.pop("tenant")
        else:
            # A superuser may deliberately create an unscoped device, matching
            # the existing admin behaviour. Tenant-aware operators never see
            # this field and receive their request tenant on save.
            self.fields["tenant"].required = False

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.HiddenInput):
                continue  # picker-driven fields carry no Bootstrap control styling
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css = "form-select"
                if name in self.SEARCHABLE_SELECT_FIELDS:
                    css += " is-tom-select"  # searchable dropdown, enhanced by theme.js
                    # Give Tom Select a real placeholder. Without this it falls back
                    # to the empty option's "---------" label, which reads as content
                    # rather than a greyed hint; data-placeholder takes precedence
                    # (Tom Select getSettings) so the "---------" never surfaces.
                    field.widget.attrs["data-placeholder"] = _("Type to search…")
                    # Single selects read better with a single "clear all" button
                    # than a per-tag remove button (theme.js reads this opt-in).
                    field.widget.attrs["data-clear-button"] = "true"
                field.widget.attrs["class"] = css
            else:
                field.widget.attrs["class"] = "form-control"

        # Bootstrap 5 server-side validation styling: a bound field that failed
        # validation gets `.is-invalid`, so the control renders in the invalid
        # state (red border + icon). The messages themselves are emitted as
        # `.invalid-feedback` next to each control in the template.
        # https://getbootstrap.com/docs/5.3/forms/validation/
        if self.is_bound:
            for name in self.errors:
                field = self.fields.get(name)
                if field is None or isinstance(field.widget, forms.HiddenInput):
                    continue  # non-field ("__all__") or picker-driven field
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} is-invalid".strip()

    def clean_is_lentable(self):
        is_lentable = self.cleaned_data["is_lentable"]
        active_record = getattr(self.instance, "active_record", None)
        if (
            self.instance.pk
            and not self.request.user.is_superuser
            and active_record
            and active_record.record_type == Record.LENT
            and is_lentable != self.instance.is_lentable
        ):
            raise ValidationError(_("Loanability cannot be changed while this device is lent."))
        return is_lentable
