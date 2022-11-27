from django.contrib import admin

from ..models import LostRecord
from ..forms.proxyrecord_admin_form import ProxyRecordAdminForm
from .base_admin import CustomBaseProxyModelAdmin, NoModificationModelAdminMixin, RedirectToDeviceMixin


@admin.register(LostRecord)
class LostRecordAdmin(RedirectToDeviceMixin, NoModificationModelAdminMixin, CustomBaseProxyModelAdmin):
    form = ProxyRecordAdminForm
    change_form_template = 'core/lostrecord/change_form.html'

    list_display = [
        'device',
        'created_at',
        'username',
        'note',
    ]
    fields = [
        'device',
        'note',
    ]
