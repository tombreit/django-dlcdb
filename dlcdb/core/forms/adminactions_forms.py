from django import forms

from ..models import Room


class RelocateActionForm(forms.Form):
    new_room = forms.ModelChoiceField(
        queryset=Room.objects.all(),
    )
