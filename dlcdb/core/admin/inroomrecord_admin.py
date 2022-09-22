from django.contrib import admin

from ..models import InRoomRecord, Device
from ..forms.inroomrecordadmin_form import InroomRecordAdminForm
from .base_admin import CustomBaseModelAdmin, RedirectToDeviceMixin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(RedirectToDeviceMixin, CustomBaseModelAdmin):
    form = InroomRecordAdminForm
    change_form_template = 'core/inroomrecord/change_form.html'
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

    def add_view(self, request, form_url='', extra_context=None):
        device_id = request.GET.get('device')
        device = Device.objects.get(id=device_id)
        extra_context = extra_context or {}
        extra_context['localize_device'] = device
        return super().add_view(
            request, form_url, extra_context=extra_context,
        )

    def has_add_permission(self, request):
        return True
