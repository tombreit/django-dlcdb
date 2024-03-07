# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from ..models.room import RoomReconcile


class ReconcileRoomsForm(forms.Form):
    # rooms_csv_file = forms.FileField()
    rooms_csv_file = forms.ModelChoiceField(
        queryset=RoomReconcile.objects.all(),
        empty_label=None,
    )
