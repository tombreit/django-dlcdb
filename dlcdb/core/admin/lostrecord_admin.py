from django.contrib import admin

from ..models import LostRecord
from .base_admin import NoModificationModelAdminMixin, RedirectToDeviceMixin
from .record_admin import CustomRecordModelAdmin


@admin.register(LostRecord)
class LostRecordAdmin(RedirectToDeviceMixin, NoModificationModelAdminMixin, CustomRecordModelAdmin):
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
