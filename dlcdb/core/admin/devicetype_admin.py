from django.contrib import admin

from ..models import DeviceType
from ..utils.helpers import get_has_note_badge
from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin
from .filters.has_note_filter import HasNoteFilter


@admin.register(DeviceType)
class DeviceTypeAdmin(SoftDeleteModelAdmin, CustomBaseModelAdmin):
    list_display = (
        'name',
        'prefix',
        'has_note',
    ) + CustomBaseModelAdmin.list_display

    list_filter = (
        HasNoteFilter,
    )
    
    search_fields = (
        'name',
        'prefix',
    )

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'prefix',
                'note',
            )
        }),
        ('Informal', {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'modified_at',
                'user',
                'username',
                ('deleted_at', 'deleted_by',),
            )
        })
    )

    @admin.display(description='Has Note?')
    def has_note(self, obj):
        return get_has_note_badge(obj_type="device_type", has_note=obj.note)

