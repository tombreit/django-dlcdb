# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.similar import SimilarNames, check_similar_names

from .models import Branding

# The logo fields take SVG only (validate_logo_image_file_extension); the file picker offers just those.
SVG_ONLY = forms.ClearableFileInput(attrs={"accept": ".svg"})


class BrandingForm(forms.ModelForm):
    class Meta:
        model = Branding
        fields = [
            "organization_name_en",
            "organization_name_de",
            "organization_abbr",
            "organization_url",
            "organization_street",
            "organization_zip_code",
            "organization_city",
            "organization_it_dept_name",
            "organization_it_dept_phone",
            "organization_it_dept_email",
            "organization_logo_black",
            "organization_figurative_mark",
            "room_plan",
            "documentation_url",
        ]
        widgets = {"organization_logo_black": SVG_ONLY, "organization_figurative_mark": SVG_ONLY}

    class Media:
        js = ["organization/js/contents.js"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class NameForm(forms.ModelForm):
    """
    An organizational unit or a position: a name only, compared with the
    existing ones on add (theme.similar). Built per model below.
    """

    similar_names = SimilarNames(fields=("name",))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].help_text = _(
            "The HR API sync finds the entries it fills by their name: after a rename, its next run adds the old "
            "name again."
        )
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        check_similar_names(self)
        return cleaned_data


OrganizationalUnitForm = forms.modelform_factory(OrganizationalUnit, form=NameForm, fields=["name"])
OrganizationalPositionForm = forms.modelform_factory(OrganizationalPosition, form=NameForm, fields=["name"])
