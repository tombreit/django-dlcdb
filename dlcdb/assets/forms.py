# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Device, Room


class RelocateForm(forms.Form):
    """
    Relocate form: move one or more devices to a single target room. ``devices``
    is a multi-select picker (each chosen device contributes its own hidden
    input, see ``theme/js/picker.js``); ``new_room`` is a single-select picker.
    The form only validates that real devices and a non-deleted room were chosen.

    The caller passes ``device_queryset`` (tenant-scoped) so validation rejects a
    device pk from another tenant instead of relocating it.
    """

    devices = forms.ModelMultipleChoiceField(
        queryset=Device.objects.none(),
        widget=forms.MultipleHiddenInput,
        error_messages={"required": _("Please select at least one device to move.")},
    )
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.filter(deleted_at__isnull=True),
        widget=forms.HiddenInput,
        error_messages={"required": _("Please select a target room.")},
    )

    def __init__(self, *args, device_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if device_queryset is not None:
            self.fields["devices"].queryset = device_queryset
