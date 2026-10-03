# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.utils.translation import gettext_lazy as _

# "Older than" choices on the cleanup page, in months.
AGE_CHOICES = (6, 12, 24, 36)


class RemoveOldEntriesForm(forms.Form):
    months = forms.TypedChoiceField(
        choices=[(months, months) for months in AGE_CHOICES],
        coerce=int,
        label=_("Older than (months)"),
    )
