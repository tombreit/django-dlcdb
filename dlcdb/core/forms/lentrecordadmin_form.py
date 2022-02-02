from django import forms

from ..models import LentRecord


class LentRecordAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Declaring some fields as required for this admin
        required_fields = [
            'person',
            'lent_start_date',
            'lent_desired_end_date',
        ]

        # Helper function
        if required_fields:
            for key in self.fields:
                if key in required_fields:
                    self.fields[key].required = True

    class Meta:
        model = LentRecord
        exclude = []
