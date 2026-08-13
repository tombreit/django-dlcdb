# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Device, LentRecord, Person, Record, Room
from dlcdb.core.models.record import LOST_DEVICE_NOT_LENDABLE
from dlcdb.theme.widgets import DevicePickerField, TomSelectWidget

from .pickers import lend_queryset


class LendableDeviceSelectForm(forms.Form):
    """
    The "which device?" step of the lending screen's picker mode: a single-select
    picker (see ``dlcdb.theme.widgets.DevicePickerWidget``) over the devices that
    can be lent right now. Kept separate from ``LendingForm`` because it picks a
    ``core.Device`` while ``LendingForm`` edits the resulting ``LentRecord``; the
    view resolves the device's available INROOM record before lending.
    """

    device = DevicePickerField(
        source="lend",
        queryset=Device.objects.none(),
        label=_("Available device"),
        placeholder=_("Search by EDV/Inv. no., manufacturer…"),
        error_messages={"required": _("Please select a device to lend.")},
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        if request is not None:
            # Scope to the tenant-visible, available devices so re-render and
            # validation both reject an out-of-scope device pk.
            self.fields["device"].queryset = lend_queryset(request)
            # Let the widget gate the selected card's admin link on the user's perm.
            self.fields["device"].widget.user = request.user


class LendingForm(forms.ModelForm):
    """
    Lend / return / edit form for a single lending, used by the standalone
    lending detail view. Replaces ``LentRecordAdminForm``.

    The ``person`` field is a hidden input driven by the HTMX live-search
    person picker (see ``theme/js/picker.js``); ``record_type`` carries the
    device's current state so ``clean()`` can block lending a "lost" device,
    mirroring ``LentRecordAdminForm``.

    Ending a lending is not part of this form: ``lent_end_date`` lives in
    ``LendingReturnForm``, so editing a lending can never (accidentally or via a
    hand-crafted POST) return the device.
    """

    def __init__(self, *args, record_type=None, **kwargs):
        self.record_type = record_type
        super().__init__(*args, **kwargs)

        for field_name in ("person", "room", "lent_start_date", "lent_desired_end_date"):
            self.fields[field_name].required = True

        # Default "Lent from" to today for a new lending; an existing lending
        # keeps its stored start date.
        if not self.instance.lent_start_date:
            self.initial["lent_start_date"] = timezone.localdate()

        # The picker only ever submits a person id; no need to render the full
        # (potentially huge) person queryset as <option>s.
        self.fields["person"].queryset = Person.objects.all()
        self.fields["room"].queryset = Room.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        if self.record_type == Record.LOST:
            raise ValidationError(LOST_DEVICE_NOT_LENDABLE)
        return cleaned_data

    class Meta:
        model = LentRecord
        fields = [
            "person",
            "room",
            "lent_start_date",
            "lent_desired_end_date",
            "sync_lent_end_date",
            "lent_reason",
            "lent_accessories",
            "lent_note",
        ]
        widgets = {
            "person": forms.HiddenInput(),
            "sync_lent_end_date": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            # The format pairing is required to populate native date inputs from
            # the model instance (see the licenses form for the same gotcha).
            "lent_start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "lent_desired_end_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "room": TomSelectWidget(),
            "lent_reason": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "lent_accessories": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "lent_note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class LendingReturnForm(forms.ModelForm):
    """
    Acknowledge the return of an active lending: the end date (prefilled with
    today when the return screen is opened) plus the free-text fields, so the
    device's condition can be recorded while it is handed back.

    Deliberately narrow. Returning is a lifecycle transition, not an edit of the
    lending itself: who borrowed it, from where and for how long are only
    editable through ``LendingForm``, are not fields here, and so
    ``save(commit=False)`` leaves their columns at their stored values -- no
    disabled inputs to round-trip, and a lending with e.g. no desired return date
    stays returnable.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lent_end_date"].required = True

        # Opening the return screen means "this comes back now"; a date already
        # stored on the record wins (re-opening an acknowledged return).
        if not self.instance.lent_end_date:
            self.initial["lent_end_date"] = timezone.localdate()

    class Meta:
        model = LentRecord
        fields = [
            "lent_end_date",
            "lent_reason",
            "lent_accessories",
            "lent_note",
        ]
        widgets = {
            # The format pairing is required to populate native date inputs from
            # the model instance (see LendingForm for the same gotcha).
            "lent_end_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "lent_reason": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "lent_accessories": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "lent_note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
