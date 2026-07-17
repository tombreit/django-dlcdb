# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from dlcdb.core.models import Person
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.widgets import TomSelectWidget


class PersonForm(forms.ModelForm):
    """
    The DLCDB-owned person fields. All ``udb_*`` fields are mirrored from the
    UDB sync and deliberately never exposed as form fields; a person matched
    with a UDB person (``udb_person_uuid`` set) is not editable at all — the
    views enforce that.
    """

    class Meta:
        model = Person
        fields = [
            "last_name",
            "first_name",
            "email",
            "organizational_unit",
        ]
        widgets = {
            "organizational_unit": TomSelectWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
