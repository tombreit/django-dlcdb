from django import forms
from ..models import Record, Device
from ..models import RemovedRecord


class RemovedRecordAdminForm(forms.ModelForm):

    def clean(self):

        device = self.cleaned_data['device']
        active_record_type = device.active_record.record_type

        if active_record_type == Record.REMOVED:
            raise forms.ValidationError('Record already of type "REMOVED" - can not be removed again!')
        return self.cleaned_data