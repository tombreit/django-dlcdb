# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from dlcdb.core.models import Room
from dlcdb.theme.forms import add_bootstrap_classes


class RoomForm(forms.ModelForm):
    """The editable fields of a room.

    UUID, QR code and audit values remain model data: they are generated, not
    operator input. The single auto-return/external room invariants live in
    ``Room.save()`` and are not duplicated here.
    """

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
            "description": forms.Textarea(attrs={"rows": 3}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
