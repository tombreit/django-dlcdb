import csv
import datetime
from django.db.models import Q
from django.contrib import admin
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils import timezone, dateformat
from django.db.models import Count
from django.utils.http import urlencode
from django.utils.html import format_html
from django.urls import reverse

from ..models import Device, Room, DeviceType, Supplier, Manufacturer
from ..utils.helpers import get_denormalized_user


class CustomBaseModelAdmin(admin.ModelAdmin):
    """
    Base class for all admins which should track request.user.
    """

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        return tuple(self.readonly_fields) + (
            "created_at",
            "modified_at",
            "user", 
            "username",
        )

    """
    We need both: modified save_model and save_formset to capture all save
    actions. Sorry, but I do not know why...
    """

    # https://docs.djangoproject.com/en/dev/ref/contrib/admin/#modeladmin-methods
    def save_model(self, request, obj, form, change):
        obj.user, obj.username = get_denormalized_user(request.user)
        super().save_model(request, obj, form, change)

    # https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.save_formset
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            instance.user, instance.username = get_denormalized_user(request.user)
            instance.save()
        formset.save_m2m()


class CustomBaseProxyModelAdmin(CustomBaseModelAdmin):
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
        extra_context['device'] = device
        return super().add_view(
            request, form_url, extra_context=extra_context,
        )


class SoftDeleteModelAdmin(admin.ModelAdmin):
    list_display = (
        # "is_not_soft_deleted",
    )

    def get_readonly_fields(self, request, obj=None):
        return tuple(super().get_readonly_fields(request, obj=None)) + (
            "deleted_at",
            "deleted_by",
        )

    # def clean(self):
    #     if model.with_softdeleted_objects.filter(crit=crit).exists():
    #         raise ValidationError('A soft-deleted obj with this crit already exists.')

    def delete_model(self, request, obj):
        obj.deleted_by = request.user
        obj.delete()

    def get_queryset(self, request):
        try:
            if request.user.is_superuser:
                queryset = self.model.with_softdeleted_objects.all()
            else:
                queryset = self.model.objects.all()
        except Exception:
            queryset = self.model._default_manager.all()

        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    # To get a nice green icon for not soft deleted objects
    def is_not_soft_deleted(self, obj):
        return False if obj.deleted_at else True
    is_not_soft_deleted.boolean = True
    is_not_soft_deleted.short_description = 'Not soft deleted'


class NoModificationModelAdminMixin(object):
    ordering = ['-modified_at']

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return False


class RedirectToDeviceMixin(object):
    """
    Most of our admins redirect to the admin instance changelist after adding
    a new record. But we like to be redirected to the corresponding device admin.
    """

    def response_post_save_add(self, request, obj):
        from ..models import Device

        device_obj = Device.objects.get(id=obj.device_id)

        return HttpResponseRedirect(
            reverse('admin:core_device_change', args=[device_obj.pk])
        )


class ExportCsvMixin:

    @admin.action(description='Export selected as CSV')
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        _now = dateformat.format(timezone.now(), 'Y-m-d_H-i-s')
        filename = f"dlcdb_export_{_now}_{meta.app_label}-{meta.model_name}.csv"

        fieldnames = [field.name for field in meta.fields]

        if 'active_record' in fieldnames:
            fieldnames.extend(["room", "record_created_at"])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f"attachment; filename={filename}"
        writer = csv.DictWriter(
            response,
            fieldnames=fieldnames,
            dialect='excel-tab',
            # delimiter=';',
            # quotechar='"',
            quoting=csv.QUOTE_ALL,
            extrasaction='raise',
        )

        writer.writeheader()
        for obj in queryset:
            row_data = {}
            for field in fieldnames:
                fieldname = field
                fielddata = None

                if field == 'active_record':
                    fielddata = obj.active_record.record_type if obj.active_record else "no record set"
                elif field == 'record_created_at':
                    fielddata = obj.active_record.created_at if obj.active_record else "no record set"
                elif field == 'room':
                    fielddata = getattr(obj.active_record.room, "number", None) if obj.active_record else "no record set"
                else:
                    fielddata = getattr(obj, field)

                if isinstance(fielddata, datetime.datetime):
                    fielddata = (f'{fielddata:%Y-%m-%d %H:%M}')

                row_data.update({fieldname: fielddata})
    
            row = writer.writerow(row_data)

        # Does not work as we do not trigger a HttpResponseRedirect which could display that message.
        # self.message_user(request, f'Export file "{filename}" created.', messages.SUCCESS)

        return response


class DeviceCountMixin:
    """
    Adds the count of devices for the given related model to the queryset
    and displays them as in Django admins list_display.
    """

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))  # we could get lists or tuples
        if not 'get_assets_count' in list_display:
            list_display.append('get_assets_count')
        return list(list_display)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if self.model == Room:
            queryset = queryset.annotate(
                _assets_count=Count("record", distinct=True,
                    filter=Q(record__is_active=True)
                ),
            )
        else:
            queryset = queryset.annotate(
                _assets_count=Count("device", distinct=True),
            )

        return queryset

    @admin.display(
        description='Assets',
        ordering='-_assets_count',
    )
    def get_assets_count(self, obj):
        query_key = None

        if self.model == Room:
            query_key = "active_record__room__id__exact"
        elif self.model == DeviceType:
            query_key = "device_type__id__exact"
        elif self.model == Manufacturer:
            query_key = "manufacturer__id__exact"
        elif self.model == Supplier:
            query_key = "supplier__id__exact"
            
        if query_key:
            result = format_html(
                '<a class="badge badge-info" href="{url}?{query_kwargs}">{count}</a>',
                url=reverse('admin:core_device_changelist'),
                query_kwargs=urlencode({query_key: obj.pk}),
                count=obj._assets_count,
            )
        else:
            result = format_html(
                '<span class="badge badge-info">{count}</span>',
                count=obj._assets_count,
            )

        return result

