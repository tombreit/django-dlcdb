import json
from django.conf import settings
from django.urls import reverse
from django.utils.html import mark_safe, format_html
from django.contrib import admin
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from simple_history.admin import SimpleHistoryAdmin

from dlcdb.tenants.admin import TenantScopedAdmin

from ..models import Device, Record
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

    def get_list_display(self, request):
        """
        Return a sequence containing the fields to be displayed on the
        changelist.
        """
        list_display = super().get_list_display(request)
        if settings.DEVICE_HIDE_FIELDS:
            list_display = list(list_display)
            list_display = [entry for entry in list_display if entry not in settings.DEVICE_HIDE_FIELDS]
            # set() operations do not preserve order
            # list_display = list(set(list_display) - set(settings.DEVICE_HIDE_FIELDS))
        return list_display

    def get_fieldsets(self, request, obj=None):
        orig_fieldsets = super().get_fieldsets(request, obj)

        # TODO: Possibly dangerous serialization to text format, str.replace()
        # our DEVICE_HIDE_FIELDS and de-serializize to django fieldsets.
        if settings.DEVICE_HIDE_FIELDS:
            _new_fieldsets = json.dumps(orig_fieldsets)
            for hide_field in settings.DEVICE_HIDE_FIELDS:
                _new_fieldsets = _new_fieldsets.replace(f'"{hide_field}",', '')
            new_fieldsets = json.loads(_new_fieldsets)

            # new_fieldsets = []
            # for fieldset in orig_fieldsets:
            #     fieldset = list(fieldset)
            #     print(f"{fieldset=}")
            #     print(f"{type(fieldset)=}")
            #     orig_fields = list(fieldset[1].get('fields'))
            #     print(f"{orig_fields=}")
            #     print(f"{type(orig_fields)=}")

            #     new_fields =[]

            #     for entry in orig_fields:
            #         print(f"{entry=}")
            #         print(f"{type(entry)=}")
            #         if isinstance(entry, str) and not entry in settings.DEVICE_HIDE_FIELDS:
            #             new_fields.append(entry)
            #         elif isinstance(entry, tuple):
            #             new_subentry = []
            #             for subentry in entry:
            #                 if isinstance(subentry, str) and not subentry in settings.DEVICE_HIDE_FIELDS:
            #                     new_subentry.append(subentry)

            # for  group in get_field_set_groups: #logic to  get the field set group
            #      fields = []
            #     for field in  get_group_fields: #logic to get the  group fields
            #          fields.append(field)
            #      fieldset_values = {"fields":  tuple(fields), "classes": ['collapse']}
            #      fieldsets.append((group,  fieldset_values))

            fieldsets = tuple(new_fieldsets)
        else:
            fieldsets = orig_fieldsets
        return fieldsets

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('active_record', 'active_record__room', 'device_type', 'manufacturer')
        )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Add add_links to the context in order to show a dropdown to create the records
        """
        obj = Device.with_softdeleted_objects.get(pk=object_id)

        extra_context = extra_context or {}
        extra_context.update({
            'record_add_links': self.get_record_add_links(obj),
            'current_record_infos': self.get_current_record_infos(obj),
            'has_record_notes_badge': self.has_record_notes_badge(request, object_id),
        })
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def get_current_record_infos(self, obj):
        """
        Returns a list of dicts with infos for the current state of the
        device.
        """
        current_record_infos = []
        active_record = obj.active_record

        if not active_record:
            current_record_infos.append(dict(
                label="No current record",
                css_classes="btn btn-warning disabled",
            ))
        else:
            if active_record.room:
                current_record_infos.append(dict(
                    css_classes="btn btn-info",
                    title="{text} {obj}".format(text=_('In room'), obj=active_record.room.number),
                    url=f"{reverse('admin:core_device_changelist')}?active_record__room__id__exact={active_record.room.id}",
                    label=active_record.room.number,
                ))

            # Common infos for all record types
            active_record_type = active_record.record_type
            record_type_info = {}

            if active_record_type == Record.INROOM:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    title=_("Relocate device"),
                    url=f"{reverse('core:core_devices_relocate')}?ids={obj.pk}",
                    label=active_record.get_record_type_display,
                )
            elif active_record_type == Record.LENT:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    url=reverse("admin:core_lentrecord_change", args=[active_record.pk]),
                    label=f"an {active_record.person }",
                    title=_("Edit lending"),
                )
            elif active_record_type == Record.ORDERED:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    label=active_record.get_record_type_display,
                )
            elif active_record_type == Record.REMOVED:
                record_type_info = dict(
                    css_classes="btn btn-warning",
                    url=reverse("admin:core_record_change", args=[active_record.pk]),
                    label=active_record.get_record_type_display,
                )
            elif active_record_type == Record.LOST:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f"{reverse('admin:core_record_changelist')}?device__id__exact={obj.pk}",
                    label=active_record.get_record_type_display,
                    title=_("Previous records for this device"),
                )
            else:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f'{reverse("admin:core_record_changelist")}?device__id__exact={obj.pk}',
                    label=_("Unknown record type! Contact your administrator!"),
                )

            current_record_infos.append(record_type_info)

        return current_record_infos

    def get_record_add_links(self, obj):
        """
        Returns a list of dicts each representing an add link in order to display
        dropdowns to create records for a given device.
        """
        add_links = []
        for record_value, record_label in Record.RECORD_TYPE_CHOICES:
            if record_value == Record.ORDERED:
                continue
            elif record_value == Record.LENT:
                if obj.active_record and obj.active_record.record_type == Record.LENT:
                    add_links.append(dict(
                        url=reverse("admin:core_lentrecord_change", args=[obj.active_record.pk]),
                        label=_('Verleih'),
                    ))
                elif obj.is_lentable:
                    add_links.append(dict(
                        url=reverse("admin:core_lentrecord_change", args=[obj.active_record.pk]),
                        label=_('Verleihen'),
                    ))
            else:
                add_links.append(dict(
                    label=record_label,
                    url=f"{Record.get_proxy_model_by_record_type(record_value).get_admin_action_url()}?device={obj.id}"
                ))

        return add_links



    @admin.display(description='Records')
    def get_record_info_display(self, obj):
        try:
            # current record may be none in case this device does
            # not have any records yet.
            ctx = dict(
                add_links=self.get_record_add_links(obj),
                current_record_infos=self.get_current_record_infos(obj),
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
