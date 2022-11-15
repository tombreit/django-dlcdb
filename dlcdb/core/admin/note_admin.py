from django.contrib import admin

from ..models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['pk', 'text', 'inventory', 'device', 'room', 'created_at']
    list_filter = ['inventory', 'room']
    search_fields = ['text', 'device__edv_id', 'device__sap_id', 'room__number']
