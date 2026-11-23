# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout
from django import forms

from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.similar import SimilarNames, check_similar_names

from .models import AssignedThing, Thing


class AssignedThingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.field_template = "bootstrap5/layout/inline_field.html"
        self.helper.layout = Layout(
            "person",
            "thing",
            HTML(
                """
                  <button type="submit" name="submit" class="btn btn-danger ml-1">
                    <i class="bi bi-plus-circle-fill"></i>
                  </button>
            """
            ),
        )

    class Meta:
        model = AssignedThing
        fields = "__all__"
        widgets = {
            "person": forms.HiddenInput(),
        }


class ThingForm(forms.ModelForm):
    """A thing of the catalogue: its name, compared with the existing ones on add (theme.similar)."""

    similar_names = SimilarNames(fields=("name",))

    class Meta:
        model = Thing
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        check_similar_names(self)
        return cleaned_data
