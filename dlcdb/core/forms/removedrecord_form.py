from django import forms
from ..models import Record
from .proxyrecord_admin_form import ProxyRecordAdminForm

class RemovedRecordAdminForm(ProxyRecordAdminForm):

    def clean(self):
        device = self.cleaned_data['device']
        active_record_type = device.active_record.record_type

        if active_record_type == Record.REMOVED:
            raise forms.ValidationError('Record already of type "REMOVED" - can not be removed again!')
        return self.cleaned_data
