# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path

from django import forms
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q

from dlcdb.core.models import Person, Room
from dlcdb.core.utils.helpers import shrink_photo
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.similar import SimilarNames, check_similar_names
from dlcdb.theme.widgets import TomSelectMultipleWidget, TomSelectWidget


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
            "organizational_positions",
            "room",
            "photo",
        ]
        widgets = {
            "organizational_unit": TomSelectWidget(),
            "organizational_positions": TomSelectMultipleWidget(),
            "room": TomSelectWidget(),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
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

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        # A new upload is stored shrunk, like the HR sync's photos. The stored
        # file (no upload) and False ("Clear") pass as they are.
        if isinstance(photo, UploadedFile):
            photo = ContentFile(shrink_photo(photo), name=f"{Path(photo.name).stem}.jpg")
        return photo

    def clean(self):
        cleaned_data = super().clean()
        check_similar_names(self)
        return cleaned_data
