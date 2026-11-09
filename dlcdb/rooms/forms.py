# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import re

from django import forms
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Room
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.similar import SimilarNames, check_similar_names


class RoomForm(forms.ModelForm):
    """The editable fields of a room.

    UUID, QR code and audit values remain model data: they are generated, not
    operator input. The single auto-return/external room invariants live in
    ``Room.save()`` and are not duplicated here.
    """

    # Compared with the existing rooms on add (theme.similar): identical numbers
    # only, since neighbouring rooms (F1.01, F1.02) look alike. Nicknames repeat
    # legitimately.
    similar_names = SimilarNames(fields=("number",), fuzzy=False)

    class Meta:
        model = Room
        fields = [
            "number",
            "nickname",
            "description",
            "website",
            "note",
            "is_auto_return_room",
            "is_external",
            "is_default_license_room",
        ]
        widgets = {
            "number": forms.TextInput(attrs={"class": "font-monospace"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        check_similar_names(self)
        return cleaned_data


class RoomRenameForm(forms.Form):
    """The regular expression of a batch rename (``rooms.rename``)."""

    pattern = forms.CharField(
        label=_("Pattern"),
        help_text=_("A regular expression in Python syntax, matched against every room number."),
        widget=forms.TextInput(attrs={"class": "font-monospace", "placeholder": r"^(\d+)$"}),
    )
    replacement = forms.CharField(
        label=_("Replacement"),
        required=False,
        help_text=_("The new room number. \\1, \\2, … insert the pattern's groups."),
        widget=forms.TextInput(attrs={"class": "font-monospace", "placeholder": r"G\1"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        if "pattern" not in cleaned_data:
            return cleaned_data
        try:
            regex = re.compile(cleaned_data["pattern"])
        except re.error as error:
            self.add_error("pattern", _("Invalid regular expression: %(error)s") % {"error": error})
            return cleaned_data
        # sub() checks the replacement's group references even when nothing
        # matches; an unknown group name raises IndexError.
        try:
            regex.sub(cleaned_data["replacement"], "")
        except (re.error, IndexError) as error:
            self.add_error("replacement", _("Invalid replacement: %(error)s") % {"error": error})
        return cleaned_data
