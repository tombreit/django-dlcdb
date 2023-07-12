from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from crispy_forms.bootstrap import FieldWithButtons, StrictButton

from dlcdb.core.models import Note


class InventorizeRoomForm(forms.Form):
    uuids = forms.CharField(
        required=False,
        label="Found UUIDs",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
            }
        ),
    )  # do not set disabled/readonly=True, as these fields will not appear in POST
    # room = forms.CharField(widget=forms.HiddenInput())


class DeviceAddForm(forms.Form):
    def __init__(self, *args, **kwargs):
        device_choices = kwargs.pop("device_choices")
        super().__init__(*args, **kwargs)
        self.fields["device"] = forms.ChoiceField(choices=device_choices)

    # device = forms.ChoiceField(choices=device_choices)
    room = forms.CharField(widget=forms.HiddenInput())


class DeviceSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.template_pack = "bootstrap4"
        # self.form_tag = True
        self.helper.form_method = "get"
        self.helper.disable_csrf = True

        self.helper.layout = Layout(
            Row(
                Column('q'), 
                Column('device_type'),
                Column('record'), 
            )
        )

class RoomSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.template_pack = "bootstrap4"
        self.form_tag = False
        self.helper.form_method = "get"
        self.helper.disable_csrf = True

        self.helper.layout = Layout(
            FieldWithButtons(
                "q",
                StrictButton(
                    '<i class="fas fa-search"></i>', type="submit", css_class="btn-sm btn btn-outline-primary"
                ),
            ),
        )


class NoteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.hx_post_url = kwargs.pop("hx_post_url", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_tag = False
        # self.helper.form_tag = True
        # self.helper.form_class = "form-inline note-update-form"
        # self.helper.attrs = {
        #     'hx_post': self.hx_post_url,
        #     'hx_target': 'this',
        #     'hx_on': "htmx:afterRequest: alert('Making a request!')",
        # }

    class Meta:
        model = Note
        fields = [
            "text",
            # Do not expose these fields, they are set via the view:
            # "room",
            # "inventory",
        ]
