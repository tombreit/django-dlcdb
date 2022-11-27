from django.contrib import admin

from ..models import InRoomRecord, Device
from ..forms.proxyrecord_admin_form import ProxyRecordAdminForm
from .base_admin import CustomBaseProxyModelAdmin, RedirectToDeviceMixin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(RedirectToDeviceMixin, CustomBaseProxyModelAdmin):
    form = ProxyRecordAdminForm
    change_form_template = 'core/inroomrecord/change_form.html'
    list_display = ['device', 'created_at', 'note']
    fields = ('device', 'room', 'note')

    autocomplete_fields = [
        'room',
    ]

    def has_add_permission(self, request):
        return True
