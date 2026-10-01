# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.core.exceptions import ValidationError

from dlcdb.tenants.models import Tenant
from dlcdb.tenants.shortcuts import limit_tenant_field

from ..models import DeviceType, Room


class RelocateActionForm(forms.Form):
    def __init__(self, *args, tenants, **kwargs):
        super().__init__(*args, **kwargs)
        # A tenant change needs at least two tenants to choose from; the
        # limited queryset rejects any tenant outside the user's tenants.
        if len(tenants) > 1:
            limit_tenant_field(self.fields["new_tenant"], tenants)
        else:
            del self.fields["new_tenant"]

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
