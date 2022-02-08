from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, Div

from dlcdb.core.models import Record, LentRecord


class LendingForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.template_pack = 'bootstrap4'
        self.helper.layout = Layout(
            'device',
            Div(
                Div('lent_start_date',css_class='col-md-4',),
                Div('lent_desired_end_date',css_class='col-md-4',),
                Div('lent_end_date',css_class='col-md-4',),
                css_class='row',
            ),
            Div(
                Div('lent_accessories',css_class='col-md-6',),
                Div('lent_note', css_class='col-md-6',),
                css_class='row',
            ),
        )

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
        fields = [
            "person",
            "device",
            "room",
            'lent_start_date',
            'lent_desired_end_date',
            'lent_end_date',
            'lent_accessories',
            'lent_note',
        ]
        widgets = {
            'person': forms.HiddenInput(),
            'room': forms.HiddenInput(),
            'lent_start_date': forms.TextInput(attrs={'type': 'date'}),
            'lent_desired_end_date': forms.TextInput(attrs={'type': 'date'}),
            'lent_end_date': forms.TextInput(attrs={'type': 'date'}),
            'lent_accessories': forms.Textarea(attrs={'rows': 3}),
            'lent_note': forms.Textarea(attrs={'rows': 3}),
        }
