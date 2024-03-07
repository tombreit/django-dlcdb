# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.core.exceptions import ValidationError

from dlcdb.tenants.models import Tenant
from ..models import Room, DeviceType


class RelocateActionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.is_superuser = kwargs.pop("is_superuser", None)
        super().__init__(*args, **kwargs)

    new_tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
    )
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.all(),
        required=False,
    )
    new_device_type = forms.ModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
    )

    def clean_new_tenant(self):
        new_tenant = self.cleaned_data["new_tenant"]

        if new_tenant and not self.is_superuser:
            raise ValidationError("You must be logged in with superuser power to change the tenant!")

        return new_tenant

    def clean(self):
        cleaned_data = super().clean()
        new_tenant = cleaned_data.get("new_tenant")
        new_room = cleaned_data.get("new_room")
        new_device_type = cleaned_data.get("new_device_type")

        if not any(
            [
                new_tenant,
                new_room,
                new_device_type,
            ]
        ):
            raise ValidationError("Either a new room and/or a new tenant must be entered!")

        return cleaned_data
