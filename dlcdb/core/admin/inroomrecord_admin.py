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

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        context.update({
            'show_save_and_add_another': False,
            'show_save_and_continue': False,
        })
        return super().render_change_form(request, context, add, change, form_url, obj)

    def has_add_permission(self, request):
        return True
