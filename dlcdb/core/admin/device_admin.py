from django.conf import settings
from django.urls import reverse
from django.utils.html import mark_safe, format_html
from django.contrib import admin
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType

from simple_history.admin import SimpleHistoryAdmin

from dlcdb.tenants.admin import TenantScopedAdmin

from ..models import Device
from ..utils.helpers import get_has_note_badge
from .filters.duplicates_filter import DuplicateFilter
from .filters.recordtype_filter import HasRecordFilter
from .base_admin import  SoftDeleteModelAdmin, CustomBaseModelAdmin, ExportCsvMixin


# class NoteInline(admin.TabularInline):
#     extra = 0
#     model = Note
#     classes = ['collapse']


@admin.register(Device)
class DeviceAdmin(TenantScopedAdmin, SoftDeleteModelAdmin, SimpleHistoryAdmin, ExportCsvMixin, CustomBaseModelAdmin):
    change_form_template = 'core/device/change_form.html'
    save_as = True
    # inlines = [NoteInline]
    ordering =  ['-modified_at']  # '-active_record__created_at'

    list_filter = (
        'device_type',
        'active_record__record_type',
        'is_lentable',
        'active_record__room',
        # 'is_deinventorized',
        DuplicateFilter,
        'manufacturer',
        'series',
        HasRecordFilter,
        'active_record__inventory',
        'is_imported',
        'created_at',
        'modified_at',
    )

    search_fields = [
        'edv_id',
        'sap_id',
        'nick_name',
        'device_type__name',
        'manufacturer__name',
        'series',
        'serial_number',
        # 'uuid',
        'order_number',
    ]
    autocomplete_fields = [
        'manufacturer',
        'device_type',
        'supplier',
    ]

    list_display = (
        'edv_id',
        'sap_id',
        'device_type',
        'manufacturer',
        'series',
        'get_record_info_display',
    )  # + CustomBaseModelAdmin.list_display

    readonly_fields = (
        'is_imported',
        'imported_by',
        'get_imported_by_link',
        'is_legacy',
        'uuid',
        'qrcode_display',
        # 'qrcode',
    )

    actions = [
        'relocate',
        'export_as_csv',
    ]

    # form = DeviceAdminForm
    list_max_show_all = 5000

    fieldsets = (
        (None, {
            'fields': (
                ('edv_id', 'sap_id'),
                'device_type',
                ('is_lentable', 'is_licence'),
                # 'is_deinventorized',
                'tenant',  # TODO: set this field in TenantAdmin
            )
        }),
        ('Hersteller', {
            'fields': (
                ('manufacturer', 'series', 'serial_number')
            ),
        }),
        (None, {
            'fields': (
                'note',
            )
        }),
        ('Procurement', {
            'classes': ('collapse',),
            'fields': (
                'supplier',
                'order_number',
                ('purchase_date', 'warranty_expiration_date', 'maintenance_contract_expiration_date'),
            ),
        }),
        ('Nicks', {
            'classes': ('collapse',),
            'fields': (
                'nick_name',
                'mac_address',
                'extra_mac_addresses',
            ),
        }),
        ('Secrets', {
            'classes': ('collapse',),
            'fields': (
                ('machine_encryption_key',),
                ('backup_encryption_key',)
            ),
        }),
        ('Informal', {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'modified_at',
                'user',
                'username',
                'is_legacy',
                'is_imported',
                'get_imported_by_link',
                'uuid',
                'qrcode_display',
                # 'qrcode',
                ('deleted_at', 'deleted_by',),
            )
        })
    )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('active_record', 'active_record__room', 'device_type', 'manufacturer')
        )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Add add_links to the context in order to show a dropdown to create the records
        """
        extra_context = extra_context or {}
        extra_context.update({
            'record_add_links': Device.with_softdeleted_objects.get(pk=object_id).get_record_add_links(),
            'has_record_notes_badge': self.has_record_notes_badge(request, object_id),
        })
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    @admin.display(description='Records')
    def get_record_info_display(self, obj):
        try:
            # current record may be none in case this device does
            # not have any records yet.
            ctx = dict(
                add_links=obj.get_record_add_links(),
                obj=obj,
                list_view=True,
            )
            return render_to_string('core/device/record_snippet.html', ctx)
        except:
            import traceback
            traceback.print_exc()
            raise

    @admin.display(description='QR Code')
    def qrcode_display(self, obj):
        return mark_safe('<img src="{url}" width="{width}" height="{height}">'.format(
            url=obj.qrcode.url,
            width=200,
            height=200,
            )
        )

    @admin.display(description='Imported via')
    def get_imported_by_link(self, obj):
        return format_html(
            '<a href="{0}">{1}</a>',
            reverse('admin:core_importerlist_change', args=(obj.imported_by.pk,)),
            obj.imported_by,
        )

    def has_record_notes_badge(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj.has_record_notes():
            return get_has_note_badge(obj_type="record", level="warning", has_note=True)

    # Custom Django admin actions
    # https://docs.djangoproject.com/en/3.2/ref/contrib/admin/actions/
    def relocate(self, request, queryset):
        """
        Bulk relocating devices to a new room. Uses an intermediate django admin page
        for asking for new room.
        """
        selected = queryset.values_list('pk', flat=True)
        ct = ContentType.objects.get_for_model(queryset.model, for_concrete_model=False)
        return HttpResponseRedirect('/admin/core/devices/relocate/?ct=%s&ids=%s' % (
            ct.pk,
            ','.join(str(pk) for pk in selected),
        ))

    # django-simple-history
    # https://django-simple-history.readthedocs.io/en/latest/admin.html
    history_list_display = ['get_changed_fields']

    def get_changed_fields(self, obj):
        changes = []
        prev_record = obj.prev_record
        if prev_record:
            delta = obj.diff_against(prev_record)
            for change in delta.changes:
                changes.append({
                    'field': change.field,
                    'prev_value': change.old,
                    'new_value': change.new,
                })

            context = {"changes": changes}
            return render_to_string('core/device/history_diff.html', context)
