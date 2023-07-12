from django.contrib import admin

from ..models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = [
        "text",
        "device",
        "get_device_room",
        "inventory",
        "room",
        "updated_at",
    ]
    list_filter = [
        "inventory",
        # TODO: Filter got same filter title as the next filter: room
        # "device__active_record__room",
        "room",
        "updated_at",
    ]
    search_fields = [
        "text",
        "device__edv_id",
        "device__sap_id",
        "room__number",
        "room__nickname",
    ]
    readonly_fields = [
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ]

    @admin.display(description="Device room")
    @admin.display(ordering="device__active_record__room")
    def get_device_room(self, obj):
        if hasattr(obj, "device") and obj.device:
                return obj.device.active_record.room
