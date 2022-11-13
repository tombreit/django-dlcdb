from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from crispy_forms.bootstrap import FieldWithButtons, StrictButton


class InventorizeRoomForm(forms.Form):
    uuids = forms.CharField(
        required=False,
        label="Found UUIDs",
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
            }
        ),
    )  # do not set disabled/readonly=True, as these fields will not appear in POST
    # room = forms.CharField(widget=forms.HiddenInput())


class DeviceAddForm(forms.Form):
    def __init__(self, *args, **kwargs):
        device_choices = kwargs.pop('device_choices')
        super().__init__(*args, **kwargs)
        self.fields['device'] = forms.ChoiceField(choices=device_choices)

    # device = forms.ChoiceField(choices=device_choices)
    room = forms.CharField(widget=forms.HiddenInput())


class RoomSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.template_pack = 'bootstrap4'
        self.helper.form_method = 'get'

        self.helper.layout = Layout(
            FieldWithButtons(
                'q', 
                StrictButton('<i class="fas fa-search"></i>', type="submit", css_class="btn-sm btn btn-outline-primary")
            ),
        )
