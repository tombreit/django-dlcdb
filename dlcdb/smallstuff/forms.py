# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML

from .models import AssignedThing


class AssignedThingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            "thing",
            "person",
            HTML(
                """
                <button type="submit" name="submit" class="btn btn-danger ml-1 mb-2"><i class="bi bi-plus-circle-fill"></i></button>
            """
            ),
        )

    class Meta:
        model = AssignedThing
        fields = "__all__"
        widgets = {
            "person": forms.HiddenInput(),
        }
