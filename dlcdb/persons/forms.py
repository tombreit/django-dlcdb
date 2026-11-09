# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.db.models import Q

from dlcdb.core.models import Person, Room
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.similar import SimilarNames, check_similar_names
from dlcdb.theme.widgets import TomSelectWidget


class PersonForm(forms.ModelForm):
    """
    The DLCDB-owned person fields. All ``udb_*`` fields are mirrored from the
    UDB sync and deliberately never exposed as form fields; a person matched
    with a UDB person (``udb_person_uuid`` set) is not editable at all — the
    views enforce that.
    """

    # Compared with the existing persons on add (theme.similar), synced ones
    # too: the UDB sync fills these fields as well. The e-mail address is unique
    # by itself.
    similar_names = SimilarNames(fields=("last_name", "first_name"))

    class Meta:
        model = Person
        fields = [
            "last_name",
            "first_name",
            "email",
            "organizational_unit",
            "room",
        ]
        widgets = {
            "organizational_unit": TomSelectWidget(),
            "room": TomSelectWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Active rooms, and the person's own room even when it was deactivated
        # since: otherwise the select would show none, and saving would drop it.
        # Before add_bootstrap_classes, which validates a bound form.
        if self.instance.room_id:
            self.fields["room"].queryset = Room.with_softdeleted_objects.filter(
                Q(deleted_at__isnull=True) | Q(pk=self.instance.room_id)
            )
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        check_similar_names(self)
        return cleaned_data
