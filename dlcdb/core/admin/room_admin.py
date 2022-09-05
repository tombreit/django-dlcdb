from django.contrib import admin
from django.utils.html import mark_safe
from django.utils.html import format_html
from django.urls import reverse

from ..models import Room
from ..models.room import RoomReconcile
from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin


@admin.register(Room)
class RoomAdmin(SoftDeleteModelAdmin, CustomBaseModelAdmin):
    change_list_template = 'core/room/change_list.html'
    
    list_display = (
        'number',
        'nickname',
        'description',
        'is_auto_return_room',
        'is_external',
    ) # + CustomBaseModelAdmin.list_display

    list_filter = [
        'is_auto_return_room',
        'is_external',
        'deleted_at',
    ]
    search_fields = [
        'number',
        'nickname',
        # 'uuid',
    ]
    # exclude = ['qrcode']
    readonly_fields = [
        'uuid',
        'qrcode_display',
        # 'qrcode',
    ]

    fieldsets = (
        (None, {
            'fields': (
                'number',
                'nickname',
                'description',
                ('is_auto_return_room', 'is_external'),
            )
        }),
        ('Informal', {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'modified_at',
                'user',
                'username',
                'uuid',
                'qrcode_display',
                # 'qrcode',
                ('deleted_at', 'deleted_by',),
            )
        })
    )

    def qrcode_display(self, obj):
        return mark_safe('<img src="{url}" width="{width}" height="{height}">'.format(
            url=obj.qrcode.url,
            width=200,
            height=200,
            )
        )
    qrcode_display.short_description = 'QR Code'

    def has_delete_permission(self, request, obj=None):
        return True



@admin.register(RoomReconcile)
class RoomReconcileAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'file',
        'note',
        'get_reconcile_button',
    ]

    def get_reconcile_button(self, obj):
        return format_html(
            '<a class="btn btn-warning" href="{}">&rarr; {}</a>', 
            reverse('core:reconcile-rooms', args=[obj.id]),
            "Abgleichen"
        )
    get_reconcile_button.short_description = 'Abgleich'
