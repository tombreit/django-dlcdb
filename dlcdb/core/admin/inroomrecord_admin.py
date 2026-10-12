# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dlcdb.tenants.admin import TenantScopedRecordAdmin

from ..forms.proxyrecord_admin_form import ProxyRecordAdminForm
from ..models import InRoomRecord, Room
from ..utils.links import linked_message
from .base_admin import CustomBaseProxyModelAdmin, RedirectToDeviceMixin


@admin.register(InRoomRecord)
class InRoomRecordAdmin(TenantScopedRecordAdmin, RedirectToDeviceMixin, CustomBaseProxyModelAdmin):
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
        """
        Hides the extra save buttons. For the device the add view was opened for
        (``?device=``), passes its lending as ``current_lending`` when the device is
        lent out right now, so the form can warn that locating it ends the lending.
        """
        active_record = getattr(context.get("device"), "active_record", None)
        lent_out = active_record is not None and active_record.is_type_lent and active_record.lent_end_date is None
        context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
                "show_activate_deactivate": False,
                "current_lending": active_record if lent_out else None,
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)
