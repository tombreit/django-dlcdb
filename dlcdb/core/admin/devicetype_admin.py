from django.contrib import admin

from ..models import DeviceType
from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin


@admin.register(DeviceType)
class DeviceTypeAdmin(SoftDeleteModelAdmin, CustomBaseModelAdmin):
    list_display = (
        'name',
        'prefix',
    ) + CustomBaseModelAdmin.list_display
    
    search_fields = (
        'name',
        'prefix',
    )

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'prefix',
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
