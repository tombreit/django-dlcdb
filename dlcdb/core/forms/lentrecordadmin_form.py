# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.core.exceptions import ValidationError

from ..models import LentRecord, Record


class LentRecordAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_fields = [
            "person",
            "lent_start_date",
            "lent_desired_end_date",
        ]

        if required_fields:
            for key in self.fields:
                if key in required_fields:
                    self.fields[key].required = True

    def clean(self):
        cleaned_data = super().clean()  # NOQA
        if self.record_type == Record.LOST:
            raise ValidationError('Device gilt aktuell als "Nicht auffindbar". Device muss zuerst lokalisiert werden.')

    class Meta:
        model = LentRecord
        exclude = []
