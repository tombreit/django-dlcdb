# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.utils.translation import gettext_lazy as _

from dlcdb.theme.forms import add_bootstrap_classes

from .models import Tenant


class TenantForm(forms.ModelForm):
    """Name and contact address. The groups are set in the matrix (views.index) only."""

    class Meta:
        model = Tenant
        fields = ["name", "contact_email"]
        labels = {
            "name": _("Name"),
            "contact_email": _("Contact email"),
        }
        help_texts = {
            "contact_email": _(
                "Receives the copies of overdue-lending reminders for this tenant's devices "
                "and is shown in email footers."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
