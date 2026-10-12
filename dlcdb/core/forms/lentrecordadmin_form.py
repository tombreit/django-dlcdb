# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from ..models import LentRecord


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
        """
        Refuses a record the lending screens cannot act on, for example a lost
        device (``LentRecord.check_lending``). The admin shows an error only from
        here; ``save_model`` would fail with a server error.
        """
        cleaned_data = super().clean()
        self.instance.check_lending()
        return cleaned_data

    class Meta:
        model = LentRecord
        exclude = []
