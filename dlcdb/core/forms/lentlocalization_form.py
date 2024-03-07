# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from dlcdb.core import models


class LentLocalizationForm(forms.ModelForm):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["room"].queryset = models.Room.objects.filter(type=models.Room.TYPE_CHOICER.ENUMS.storage)

    class Meta:
        model = models.InRoomRecord
        exclude = []
