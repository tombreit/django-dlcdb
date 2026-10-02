# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from dlcdb.theme.forms import add_bootstrap_classes

from .models import Tenant


class TenantForm(forms.ModelForm):
    """Name and contact address. The groups are set in the matrix (views.index) only."""

    class Meta:
        model = Tenant
        fields = ["name", "contact_email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
