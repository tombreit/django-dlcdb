# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from ..models import InRoomRecord, Room
from ..forms.proxyrecord_admin_form import ProxyRecordAdminForm
from ..utils.links import linked_message
from .base_admin import CustomBaseProxyModelAdmin, RedirectToDeviceMixin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(RedirectToDeviceMixin, CustomBaseProxyModelAdmin):
    form = ProxyRecordAdminForm
    change_form_template = "core/inroomrecord/change_form.html"

    list_display = [
        "device",
        "created_at",
        "note",
    ]

    fields = [
        "device",
        "room",
        "note",
    ]

    autocomplete_fields = [
        "room",
    ]

    # def has_add_permission(self, request):
    #     return True

    def response_add(self, request, obj, post_url_continue=None):
        if "_save" in request.POST:
            redirect_url = reverse("admin:core_device_changelist")
            device = obj.device
            room = Room.objects.get(pk=request.POST.get("room"))
            messages.success(
                request,
                linked_message(_("Device “{device}” moved to room “{room}”."), device=device, room=room),
            )
            return HttpResponseRedirect(redirect_url)
        else:
            return super().response_change(request, obj, post_url_continue=post_url_continue)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
                "show_activate_deactivate": False,
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)
