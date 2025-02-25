# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from dlcdb.core.models import Note


class InventorizeRoomForm(forms.Form):
    uuids = forms.CharField(
        required=False,
        label="UUIDs state",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "readonly": "readonly",  # This makes the field read-only but still included in POST
            }
        ),
    )


class DeviceAddForm(forms.Form):
    def __init__(self, *args, **kwargs):
        add_devices_qs = kwargs.pop("add_devices_qs")
        device_choices = [("", "Add device")]
        device_choices += [(f"{str(d.uuid)}", f"{d.edv_id} {d.sap_id}") for d in add_devices_qs]
        super().__init__(*args, **kwargs)

        self.fields["device"] = forms.ChoiceField(
            choices=device_choices,
            # The BS5 .form-control class is applied via TomSelect
            # widget=forms.Select(attrs={"class": "form-control"}),
        )

    room = forms.CharField(widget=forms.HiddenInput())


class DeviceSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.form_tag = False
        self.helper.disable_csrf = True

        self.helper.layout = Layout(
            Row(
                Column(Field("q", autofocus="on"), css_class="col-12 col-md-3"),
                Column("device_type", css_class="col-12 col-md-3"),
                Column("record", css_class="col-6 col-md-3"),
                Column("not_already_inventorized", css_class="col-6 col-md-3"),
            )
        )


# class RoomSearchForm(forms.Form):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.form_show_labels = False
#         self.helper.template_pack = "bootstrap4"
#         self.form_tag = False
#         self.helper.form_method = "get"
#         self.helper.disable_csrf = True
#         self.helper.layout = Layout(
#             FieldWithButtons(
#                 Field('q', autofocus="on"),
#                 StrictButton(
#                     '<i class="fas fa-search"></i>', type="submit", css_class="btn-sm btn btn-outline-primary"
#                 ),
#             ),
#         )


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
