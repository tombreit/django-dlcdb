# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.template import Template, Context
from django.urls import reverse
from django.utils.html import format_html

from ..utils.helpers import get_has_note_badge
from ..models import Record
from .base_admin import CustomBaseModelAdmin, NoModificationModelAdminMixin


class CustomRecordModelAdmin(CustomBaseModelAdmin):
    def get_attachments(self, obj):
        qs = obj.attachments.all()

        attachment_links = []
        for idx, attachment in enumerate(qs):
            if attachment.file:
                # print(f"{idx}: {attachment.title}; {attachment.file.url}")
                attachment_links.append(
                    f'<a href="{attachment.file.url}">{attachment.title}</a><br>',
                )
        return format_html("".join(attachment_links))

    get_attachments.short_description = "Get Attachments"


@admin.register(Record)
class RecordAdmin(NoModificationModelAdminMixin, CustomRecordModelAdmin):
    change_form_template = "core/record/change_form.html"
    change_list_template = "core/record/change_list.html"

    exclude = [
        "attachments",
    ]

    readonly_fields = (
        "is_active",
        "record_type",
        "device",
        "note",
        "room",
        "inventory",
        "person",
        "lent_start_date",
        "lent_end_date",
        "lent_desired_end_date",
        "lent_reason",
        "lent_accessories",
        "lent_note",
        "date_of_purchase",
        "disposition_state",
        "removed_info",
        "removed_date",
        "get_attachments",
        "effective_until",
        "assigned_device",
        # These fields are already set via get_readonly_fields() in CustomBaseModelAdmin
        # 'user',
        # 'username',
        # 'created_at',
        # 'modified_at',
    )
    list_display = [
        "get_change_link_display",
        "get_sap_id",
        "device",
        "is_active",
        "room",
        "inventory",
        "has_note",
        "user",
        "created_at",
        "effective_until",
        # 'modified_at',
    ]
    list_filter = [
        "inventory",
        "record_type",
        # 'device',
        "device__device_type",
        "device__manufacturer",
        "device__tenant",
        "person",
        "room",
        "is_active",
        "inventory",
        "disposition_state",
        "created_at",
        "modified_at",
    ]
    search_fields = [
        "device__edv_id",
        "device__sap_id",
        "person__last_name",
        "person__first_name",
        "person__email",
        "person__udb_person_last_name",
        "person__udb_person_first_name",
    ]
    actions = [
        "set_removed_sold_record",
        "set_removed_scrapped_record",
    ]

    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("device", "room", "user")

    def has_add_permission(self, request):
        return False

    @admin.display(
        ordering="device__sap_id",
        description="SAP Nr",
    )
    def get_sap_id(self, obj):
        return Template('<a href="{{url}}">{{label}}</a>').render(
            Context(
                dict(
                    url=reverse("admin:core_device_change", args=(obj.device.pk,)),
                    label=obj.device.sap_id,
                )
            )
        )

    def lookup_allowed(self, key, value):
        """
        DisallowedModelAdminLookup at /admin/core/record/
        Filtering by device__id__exact not allowed
        """
        if key in ["device__id__exact"]:
            return True
        return super().lookup_allowed(key, value)

    @admin.display(description="Has Note?")
    def has_note(self, obj):
        return get_has_note_badge(obj_type="core.record", has_note=obj.note)

    @admin.display(description="Type")
    def get_change_link_display(self, obj):
        return Template('<a href="{{url}}{{query_param}}">{{label}}</a>').render(
            Context(
                dict(
                    url=reverse("admin:core_record_change", args=(obj.id,)),
                    # Link to list of records for this device:
                    # http://127.0.0.1:8001/admin/core/record/?device__id__exact=1706
                    # url=reverse('admin:core_record_changelist'),
                    # query_param='?device__id__exact={}'.format(obj.device.pk),
                    label=obj.get_record_type_display(),
                )
            )
        )

    # Custom admin actions
    # https://docs.djangoproject.com/en/2.1/ref/contrib/admin/actions/
    @admin.display(description="Ausgewählte Records auf 'ENTFERNT' und 'VERKAUFT' setzen")
    def set_removed_sold_record(self, request, queryset):
        for item in queryset:
            # Set new removed record for item:
            record_obj = Record(
                record_type=Record.REMOVED,
                disposition_state=Record.SOLD,
                device=item.device,
                room=None,
                removed_info="Removed via custom django admin action.",
            )
            record_obj.save()

        self.message_user(request, "{} records auf ENTFERNT und VERKAUFT gesetzt.".format(queryset.count()))

    @admin.display(description="Ausgewählte Records auf 'ENTFERNT' und 'VERSCHROTTET' setzen")
    def set_removed_scrapped_record(self, request, queryset):
        for item in queryset:
            # Set new removed record for item:
            record_obj = Record(
                record_type=Record.REMOVED,
                disposition_state=Record.SCRAPPED,
                device=item.device,
                room=None,
                removed_info="Removed via custom django admin action.",
            )
            record_obj.save()

        self.message_user(request, "{} records auf ENTFERNT und VERSCHROTTET gesetzt.".format(queryset.count()))

    def changelist_view(self, request, extra_context=None):
        """
        Customized record listing admin view when only records for one device are shown.
        TODO: Get action_form object from super() write a nicer method body.
        """
        from dlcdb.core.models import Device

        try:
            device_id = int(request.GET.get("device__id__exact"))
            extra_context = extra_context or {
                "device_obj": Device.objects.get(id=device_id),
                "action_form": False,
            }
        except:  # NOQA
            pass

        return super().changelist_view(request, extra_context=extra_context)
