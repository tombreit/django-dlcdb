# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

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

from ..models import Device, Room, DeviceType, Supplier, Manufacturer, LentRecord, Record
from ..utils.helpers import get_denormalized_user


class CustomBaseModelAdmin(admin.ModelAdmin):
    """
    Base class for all admins which should track request.user.
    """

    show_facets = admin.ShowFacets.NEVER

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
            readonly_fields = tuple(readonly_fields) + ("device", "room")

        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        _device = request.GET.get("device", None)

        if _device:
            form.base_fields["device"].initial = _device

        if not obj:
            form.base_fields["device"].disabled = False

        return form

    def add_view(self, request, form_url="", extra_context=None):
        device_id = request.GET.get("device")
        extra_context = extra_context or {}

        if device_id:
            device = Device.objects.get(id=device_id)
            extra_context["device"] = device

        return super().add_view(request, form_url, extra_context=extra_context)


class SoftDeleteModelAdmin(admin.ModelAdmin):
    list_display = (
        # "is_not_soft_deleted",
    )

    def get_actions(self, request):
        """
        Only expose hard delete queryset option for superusers.
        https://docs.djangoproject.com/en/4.2/ref/contrib/admin/actions/#conditionally-enabling-or-disabling-actions
        """
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            if "hard_delete_action" in actions:
                del actions["hard_delete_action"]
        return actions

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

    @admin.action(description="Hard delete")
    def hard_delete_action(self, request, queryset):
        queryset.hard_delete()

    # To get a nice green icon for not soft deleted objects
    @admin.display(
        boolean=True,
        description="Not soft deleted",
    )
    def is_not_soft_deleted(self, obj):
        return False if obj.deleted_at else True


class NoModificationModelAdminMixin(object):
    ordering = ["-modified_at"]

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

        return HttpResponseRedirect(reverse("admin:core_device_change", args=[device_obj.pk]))


class ExportCsvMixin:
    @admin.action(description="Export selected as CSV")
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        _now = dateformat.format(timezone.now(), "Y-m-d_H-i-s")
        filename = f"dlcdb_export_{_now}_{meta.app_label}-{meta.model_name}.csv"

        fieldnames = [field.name for field in Device._meta.fields]  # .get_fields()
        RECORD_FIELDNAMES = [field.name for field in Record._meta.fields]

        if meta.model is Device:
            # fieldnames = [field.name for field in meta.fields]
            fieldnames.extend(["room", "created_at"])
            export_queryset = queryset
        elif meta.model is LentRecord:
            device_pks = queryset.values_list("device", flat=True)
            export_queryset = Device.objects.filter(pk__in=device_pks)
            fieldnames.extend(["person", "lent_desired_end_date", "room", "created_at"])

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        writer = csv.DictWriter(
            response,
            fieldnames=fieldnames,
            dialect="excel-tab",
            # delimiter=';',
            # quotechar='"',
            quoting=csv.QUOTE_ALL,
            extrasaction="raise",
        )

        writer.writeheader()
        for obj in export_queryset:
            row_data = {}
            for field in fieldnames:
                fieldname = field
                fielddata = None

                if field == "active_record":
                    fielddata = obj.active_record.record_type if obj.active_record else "no record set"

                if field in RECORD_FIELDNAMES:
                    # elif field == 'record_created_at':
                    #     fielddata = obj.active_record.created_at if obj.active_record else "no record set"
                    # elif field == 'room':
                    #     fielddata = getattr(obj.active_record.room, "number", None) if obj.active_record else "no record set"
                    # elif field == 'person':
                    #     fielddata = obj.active_record.person if obj.active_record.person else "no person set"
                    fielddata = getattr(obj.active_record, field)
                else:
                    fielddata = getattr(obj, field)

                if isinstance(fielddata, datetime.datetime):
                    fielddata = f"{fielddata:%Y-%m-%d %H:%M}"

                row_data.update({fieldname: fielddata})

            writer.writerow(row_data)

        # Does not work as we do not trigger a HttpResponseRedirect which could display that message.
        # self.message_user(request, f'Export file "{filename}" created.', messages.SUCCESS)

        return response


class DeviceCountMixin:
    """
    Adds the count of devices for the given related model to the queryset
    and displays them as in Django admins list_display.
    With some inspiration from https://forum.djangoproject.com/t/creating-an-admin-mixin-for-a-basemodel/11120
    """

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))  # we could get lists or tuples
        if "get_assets_count" not in list_display:
            list_display.append("get_assets_count")
        return list(list_display)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if self.model == Room:
            queryset = queryset.annotate(
                _assets_count=Count("record", distinct=True, filter=Q(record__is_active=True)),
            )
        else:
            queryset = queryset.annotate(
                _assets_count=Count("device", distinct=True),
            )

        return queryset

    @admin.display(
        description="Assets",
        ordering="-_assets_count",
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
                url=reverse("admin:core_device_changelist"),
                query_kwargs=urlencode({query_key: obj.pk}),
                count=obj._assets_count,
            )
        else:
            result = format_html(
                '<span class="badge badge-info">{count}</span>',
                count=obj._assets_count,
            )

        return result
