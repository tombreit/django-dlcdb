from django import forms
from django_select2.forms import Select2Widget

from ..models import LentRecord, Person


class LentRecordAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].queryset = Person.objects.all()

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

    person = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=Select2Widget()
    )

    class Meta:
        model = LentRecord
        exclude = []
