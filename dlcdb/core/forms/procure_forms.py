# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from .. import lifecycle
from ..models.device import Device
from ..models.note import Note


class ProcureForm(forms.ModelForm):
    date_of_purchase = forms.DateField()
    note = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = Device
        fields = ["manufacturer", "series", "device_type", "edv_id", "sap_id", "date_of_purchase"]

    def save(self):
        self.instance.save()
        record = lifecycle.transition_order(
            self.instance,
            date_of_purchase=self.cleaned_data["date_of_purchase"],
            user=None,
        )

        if self.cleaned_data["note"]:
            n = Note(text=self.cleaned_data["note"], device=self.instance)
            n.save()

        return record
