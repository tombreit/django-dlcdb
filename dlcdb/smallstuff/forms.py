from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, HTML
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, Div

from .models import AssignedThing


class AssignedThingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.template_pack = 'bootstrap4'
        self.helper.layout = Layout(
            'thing',
            'person',
            HTML("""
                <button type="submit" name="submit" class="btn btn-danger ml-1 mb-2"><i class="fas fa-plus"></i></button>
            """),
        )
        # self.helper.add_input(Submit('submit', '<i class="fas fa-plus"></i>', css_class='btn-primary'))

    class Meta:
        model = AssignedThing
        # fields = [
        #     "person",
        #     "thing",
        #     # "assigned_at",
        #     # "unassigned_at",
        # ]
        fields = '__all__'
        widgets = {
            'person': forms.HiddenInput(),
        }