from django import forms

from dlcdb.core.models import InRoomRecord


class InroomRecordAdminForm(forms.ModelForm):
    class Media:
        css = {'all': ('core/inroomrecord/add_form.css',)}

    class Meta:
        model = InRoomRecord
        exclude = []
