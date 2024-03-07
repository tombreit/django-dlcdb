# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from ..models import RemovedRecord
from ..forms.removedrecord_form import RemovedRecordAdminForm
from .base_admin import RedirectToDeviceMixin, CustomBaseProxyModelAdmin


@admin.register(RemovedRecord)
class RemovedRecordAdmin(RedirectToDeviceMixin, CustomBaseProxyModelAdmin):
    form = RemovedRecordAdminForm
    change_form_template = "core/record/change_form.html"
    fields = ("device", "disposition_state", "removed_info", "attachments")
    # readonly_fields = ('get_attachments',)
    list_display = ["device", "get_device", "disposition_state", "removed_info", "removed_date"]
    list_filter = ["disposition_state", "removed_date"]
    search_fields = ["device__edv_id", "device__sap_id", "removed_info"]
    autocomplete_fields = ["attachments"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj=None)
        if obj:
            # editing an existing object
            readonly_fields = readonly_fields + ("device", "disposition_state")
        return readonly_fields

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=None)

        if not obj:
            # Editing a new object
            fields = list(fields)
            try:
                fields.remove("get_attachments")
                fields = tuple(fields)
            except ValueError:
                pass

        return fields

    @admin.display(
        description="SAP",
        ordering="device__sap_id",
    )
    def get_device(self, obj):
        return obj.device.sap_id

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)
