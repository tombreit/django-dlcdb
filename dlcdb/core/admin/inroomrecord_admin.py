from os import read
from django.contrib import admin
from django import forms

from ..models import InRoomRecord
from .base_admin import CustomBaseModelAdmin, RedirectToDeviceMixin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(RedirectToDeviceMixin, CustomBaseModelAdmin):
    change_form_template = 'core/record_change_form.html'
    list_display = ['device', 'created_at', 'note']
    fields = ('device', 'room', 'note')

    autocomplete_fields = [
        'room',
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj: 
            print("editing an existing object")
            readonly_fields = tuple(readonly_fields) + ('device', 'room')
        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
 
        _device = request.GET.get('device', None)

        if _device:
            form.base_fields['device'].initial = _device

        if not obj:
            form.base_fields['device'].disabled = True

        return form

    def has_add_permission(self, request):
        return True
