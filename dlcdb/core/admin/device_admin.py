# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json

from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.contrib import admin
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from simple_history.admin import SimpleHistoryAdmin

from dlcdb.tenants.admin import TenantScopedAdmin

from ..models import Device, Record, LostRecord
from ..utils.helpers import get_has_note_badge, get_superuser_list
from .filters.duplicates_filter import DuplicateFilter
from .filters.recordtype_filter import HasRecordFilter
from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin, ExportCsvMixin


# class NoteInline(admin.TabularInline):
#     extra = 0
#     model = Note
#     classes = ['collapse']


@admin.register(Device)
class DeviceAdmin(TenantScopedAdmin, SoftDeleteModelAdmin, SimpleHistoryAdmin, ExportCsvMixin, CustomBaseModelAdmin):
    change_form_template = "core/device/change_form.html"
    save_as = True
    # inlines = [NoteInline]
    ordering = ["-modified_at"]  # '-active_record__created_at'

    list_filter = [
        "device_type",
        "active_record__record_type",
        "is_lentable",
        "active_record__room",
        "manufacturer",
        "series",
        "active_record__inventory",
        HasRecordFilter,
        DuplicateFilter,
        "is_imported",
        "created_at",
        "modified_at",
    ]

    search_fields = [
        "edv_id",
        "sap_id",
        "nick_name",
        "device_type__name",
        "manufacturer__name",
        "series",
        "serial_number",
        "order_number",
    ]

    def get_search_fields(self, request):
        search_fields = list(self.search_fields)
        if request.user.is_superuser:
            search_fields.append("uuid")
        return search_fields

    autocomplete_fields = [
        "manufacturer",
        "device_type",
        "supplier",
        "contact_person_internal",
    ]

    list_display = [
        "edv_id",
        "sap_id",
        "device_type",
        "manufacturer",
        "series",
        "get_device_actions",
    ]  # + CustomBaseModelAdmin.list_display

    readonly_fields = (
        "is_imported",
        "imported_by",
        "get_imported_by_link",
        "is_legacy",
        "uuid",
        "qrcode_display",
        # 'qrcode',
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.active_record and obj.active_record.record_type == Record.LENT:
            if "is_lentable" not in readonly:
                readonly.append("is_lentable")
        return readonly

    actions = [
        "relocate",
        "export_as_csv",
        "hard_delete_action",
        "restore_removed_to_lost",
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            # Remove the restore_to_inroom action for non-superusers
            actions.pop("restore_removed_to_lost", None)
        return actions

    # form = DeviceAdminForm
    list_max_show_all = 5000

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("edv_id", "sap_id"),
                    "device_type",
                    ("is_lentable", "is_licence"),
                    "tenant",  # TODO: set this field in TenantAdmin
                )
            },
        ),
        (
            "Hersteller",
            {
                "fields": (("manufacturer", "series", "serial_number")),
            },
        ),
        (None, {"fields": ("note",)}),
        (
            "Procurement",
            {
                "classes": ("collapse",),
                "fields": (
                    "supplier",
                    ("order_number", "cost_centre"),
                    ("purchase_date", "warranty_expiration_date"),
                    ("contract_start_date", "contract_expiration_date", "contract_termination_date"),
                    "procurement_note",
                    "contact_person_internal",
                ),
            },
        ),
        (
            "Nicks",
            {
                "classes": ("collapse",),
                "fields": (
                    "nick_name",
                    "mac_address",
                    "extra_mac_addresses",
                ),
            },
        ),
        (
            "Secrets",
            {
                "classes": ("collapse",),
                "fields": (("machine_encryption_key",), ("backup_encryption_key",)),
            },
        ),
        (
            "Informal",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "modified_at",
                    "user",
                    "username",
                    "is_legacy",
                    "is_imported",
                    "get_imported_by_link",
                    "uuid",
                    "qrcode_display",
                    # 'qrcode',
                    (
                        "deleted_at",
                        "deleted_by",
                    ),
                ),
            },
        ),
    )

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        return get_superuser_list(list_filter, "tenant", request.user.is_superuser)

    def get_list_display(self, request):
        """
        Return a sequence containing the fields to be displayed on the
        changelist.
        """
        self.request = request

        list_display = super().get_list_display(request)
        if settings.DEVICE_HIDE_FIELDS:
            list_display = list(list_display)
            list_display = [entry for entry in list_display if entry not in settings.DEVICE_HIDE_FIELDS]
            # set() operations do not preserve order
            # list_display = list(set(list_display) - set(settings.DEVICE_HIDE_FIELDS))

        return get_superuser_list(list_display, "tenant", request.user.is_superuser)

    def get_fieldsets(self, request, obj=None):
        orig_fieldsets = super().get_fieldsets(request, obj)

        # TODO: Possibly dangerous serialization to text format, str.replace()
        # our DEVICE_HIDE_FIELDS and de-serializize to django fieldsets.
        if settings.DEVICE_HIDE_FIELDS:
            _new_fieldsets = json.dumps(orig_fieldsets)
            for hide_field in settings.DEVICE_HIDE_FIELDS:
                _new_fieldsets = _new_fieldsets.replace(f'"{hide_field}",', "")
            new_fieldsets = json.loads(_new_fieldsets)
            fieldsets = tuple(new_fieldsets)
        else:
            fieldsets = orig_fieldsets
        return fieldsets

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("active_record", "active_record__room", "device_type", "manufacturer")
        )

    def get_view_on_site_url(self, obj=None):
        """
        Returns the URL to view this object on the site.
        This is used by the "View on site" link in the admin.
        If the objects get_absolute_url() method does not return a URL,
        the view_on_site link will not be shown.
        """
        if obj is None or not self.view_on_site:
            return None

        if hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """
        Add add_links to the context in order to show a dropdown to create the records
        """
        from ..models import Inventory

        obj = Device.with_softdeleted_objects.get(pk=object_id)

        extra_context = extra_context or {}
        extra_context.update(
            {
                "has_record_notes_badge": self.has_record_notes_badge(request, object_id),
                "inventory_status": {
                    "active_inventory": Inventory.objects.filter(is_active=True),
                    "already_inventorized": obj.get_current_inventory_record,
                    "inventorize_url": f"{reverse('inventory:search-devices')}?id={obj.pk}",
                },
                "state_data_rendered": render_to_string(
                    "core/device/state_btn_group.html", {"state_data": obj.get_state_data(user=request.user)}
                ),
            }
        )
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    @admin.display(description="Actions")
    def get_device_actions(self, obj):
        context = {
            "state_data": obj.get_state_data(user=self.request.user),
            "size": "sm",
        }

        return render_to_string("core/device/state_btn_group.html", context)

    @admin.display(description="QR Code")
    def qrcode_display(self, obj):
        return format_html(
            '<img src="{url}" width="{width}" height="{height}">',
            url=obj.qrcode.url,
            width=200,
            height=200,
        )

    @admin.display(description="Imported via")
    def get_imported_by_link(self, obj):
        return format_html(
            '<a href="{0}">{1}</a>',
            reverse("admin:core_importerlist_change", args=(obj.imported_by.pk,)),
            obj.imported_by,
        )

    def has_record_notes_badge(self, request, object_id):
        obj = self.get_object(request, object_id)
        # In case the object is not part of a tenant-filtered queryset,
        # we do not get any object.
        if obj and obj.has_record_notes():
            return get_has_note_badge(obj_type="core.record", has_note=True)

    # Custom Django admin actions
    # https://docs.djangoproject.com/en/3.2/ref/contrib/admin/actions/

    @admin.action(description=_("Relocate selected devices"))
    def relocate(self, request, queryset):
        """
        Bulk relocating devices to a new room. Uses an intermediate django admin page
        for asking for new room.
        """
        selected = queryset.values_list("pk", flat=True)
        ct = ContentType.objects.get_for_model(queryset.model, for_concrete_model=False)
        return HttpResponseRedirect(
            "/core/devices/relocate/?ct=%s&ids=%s"
            % (
                ct.pk,
                ",".join(str(pk) for pk in selected),
            )
        )

    @admin.action(description=_("Restore devices from REMOVED to LOST"))
    def restore_removed_to_lost(self, request, queryset):
        """
        Restore devices from REMOVED to LOST. Only for superusers.
        LOST was choosen as the target state because it is has the fewest attributes.
        The user should then be able to add the desiered record.
        """
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers may restore removed devices.", level=messages.ERROR)
            return

        restored_devices = []
        with transaction.atomic():
            for device in queryset.select_for_update():
                active = getattr(device, "active_record", None)
                if active and active.record_type == Record.REMOVED:
                    LostRecord.objects.create(
                        device=device,
                        note=f"Restored from REMOVED by {request.user.username}",
                        record_type=Record.LOST,
                    )
                    restored_devices.append(device)

        if restored_devices:
            links = format_html_join(
                ", ",
                '<a href="{}">{}</a>',
                ((reverse("admin:core_device_change", args=(d.pk,)), str(d)) for d in restored_devices),
            )
            self.message_user(
                request,
                format_html(
                    "Restored {} device(s) to LOST: {}.",
                    len(restored_devices),
                    links,
                ),
                level=messages.SUCCESS,
            )
        else:
            self.message_user(request, "No selected devices were in REMOVED state.", level=messages.INFO)

    # django-simple-history
    # https://django-simple-history.readthedocs.io/en/latest/admin.html
    history_list_display = ["get_changed_fields"]

    def get_changed_fields(self, obj):
        changes = []
        prev_record = obj.prev_record
        if prev_record:
            delta = obj.diff_against(prev_record)
            for change in delta.changes:
                changes.append(
                    {
                        "field": change.field,
                        "prev_value": change.old,
                        "new_value": change.new,
                    }
                )

            context = {"changes": changes}
            return render_to_string("core/device/history_diff.html", context)
