from django.contrib import admin

from ..models import RemovedRecord
from ..forms.removedrecord_form import RemovedRecordAdminForm
from .base_admin import RedirectToDeviceMixin
from .record_admin import CustomRecordModelAdmin


@admin.register(RemovedRecord)
class RemovedRecordAdmin(RedirectToDeviceMixin, CustomRecordModelAdmin):
    form = RemovedRecordAdminForm
    change_form_template = 'core/record/change_form.html'
    fields = ('device', 'disposition_state', 'removed_info', 'attachments', 'get_attachments')
    readonly_fields = ('get_attachments',)
    list_display = ['device', 'get_device', 'disposition_state', 'removed_info', 'removed_date']
    list_filter = ['disposition_state', 'removed_date']
    search_fields = ['device__edv_id', 'device__sap_id', 'removed_info']
    autocomplete_fields = ['attachments']

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj=None)
        if obj: 
            # editing an existing object
            readonly_fields = readonly_fields + ('device', 'disposition_state')
        return readonly_fields

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=None)

        if not obj:
            # Editing a new object
            fields = list(fields)
            try:
                fields.remove('get_attachments')
                fields = tuple(fields)
            except ValueError:
                pass

        return fields

    def get_device(self, obj):
        return obj.device.sap_id
    get_device.short_description = 'SAP'
    get_device.admin_order_field = 'device__sap_id'
