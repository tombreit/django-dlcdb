from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect

from ..models import InRoomRecord, Room
from ..forms.proxyrecord_admin_form import ProxyRecordAdminForm
from .base_admin import CustomBaseProxyModelAdmin, RedirectToDeviceMixin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(RedirectToDeviceMixin, CustomBaseProxyModelAdmin):
    form = ProxyRecordAdminForm
    change_form_template = 'core/inroomrecord/change_form.html'
    list_display = [
        'device',
        'created_at',
        'note',
    ]
    fields = [
        'device',
        'room',
        'note',
    ]

    autocomplete_fields = [
        'room',
    ]

    def has_add_permission(self, request):
        return True

    def response_add(self, request, obj, post_url_continue=None):
        if '_save' in request.POST:
            redirect_url = reverse('admin:core_device_changelist')
            device = obj.device
            room = Room.objects.get(pk=request.POST.get("room"))
            messages.success(request, f'Raumänderung nach Raum “{room}” für Device “{device}” durchgeführt.')
            return HttpResponseRedirect(redirect_url)
        else:
            return super().response_change(request, obj, post_url_continue=post_url_continue)

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        context.update({
            'show_save_and_add_another': False,
            'show_save_and_continue': False,
        })
        return super().render_change_form(request, context, add, change, form_url, obj)

