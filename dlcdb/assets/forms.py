# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Device, Room


class RelocateForm(forms.Form):
    """
    Single-device relocate form. Both fields are hidden inputs populated by the
    live-search pickers (see ``theme/js/picker.js``); the form only validates
    that a real device and a non-deleted room were chosen.

    The caller passes ``device_queryset`` (tenant-scoped) so validation rejects
    a device pk from another tenant instead of relocating it.
    """

    device = forms.ModelChoiceField(
        queryset=Device.objects.none(),
        widget=forms.HiddenInput,
        error_messages={"required": _("Please select a device to move.")},
    )
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.filter(deleted_at__isnull=True),
        widget=forms.HiddenInput,
        error_messages={"required": _("Please select a target room.")},
    )

    def __init__(self, *args, device_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if device_queryset is not None:
            self.fields["device"].queryset = device_queryset
