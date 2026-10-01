# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from simple_history.admin import SimpleHistoryAdmin

from ..core.models import Device
from ..core.utils.helpers import get_denormalized_user
from .models import Tenant
from .shortcuts import limit_tenant_field, tenant_scoped_queryset


class TenantScopedAdmin(admin.ModelAdmin):
    """
    Admin for tenant-scoped models: lists only objects of the user's tenants
    (``request.tenants``) and offers only these tenants in a ``tenant`` field
    and only their devices in any device field.
    """

    # Lookup path from the admin's model to the tenant.
    tenant_lookup = "tenant"

    def get_queryset(self, request):
        return tenant_scoped_queryset(super().get_queryset(request), request, tenant_field=self.tenant_lookup)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.related_model is Device:
            # Autocomplete widgets already search the (scoped) DeviceAdmin; this
            # also rejects a posted pk of a foreign device.
            kwargs["queryset"] = tenant_scoped_queryset(Device.objects.all(), request)
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "tenant":
            limit_tenant_field(formfield, request.tenants)
        return formfield


class TenantScopedRecordAdmin(TenantScopedAdmin):
    """For records: they carry no tenant of their own and are scoped through their device."""

    tenant_lookup = "device__tenant"


@admin.register(Tenant)
class TenantAdmin(SimpleHistoryAdmin):
    list_display = ("name", "group_names", "contact_email")
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("groups",)
    readonly_fields = ("created_at", "modified_at", "user", "username")
    actions = ["assign_devices_without_tenant"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    def save_model(self, request, obj, form, change):
        obj.user, obj.username = get_denormalized_user(request.user)
        super().save_model(request, obj, form, change)

    @admin.display(description=_("Groups"))
    def group_names(self, obj):
        """The groups whose members see this tenant; reveals groups shared by several tenants."""
        return ", ".join(group.name for group in obj.groups.all())

    def has_assign_devices_permission(self, request):
        """Assigning a tenant changes the tenant's scope and the devices alike."""
        return request.user.has_perm("tenants.change_tenant") and request.user.has_perm("core.change_device")

    @admin.action(description=_("Assign devices without tenant"), permissions=["assign_devices"])
    def assign_devices_without_tenant(self, request, queryset):
        """
        Redirect to an intermediate page listing all devices without tenant;
        the user confirms there which of them get the selected tenant.
        https://docs.djangoproject.com/en/6.1/ref/contrib/admin/actions/#actions-that-provide-intermediate-pages
        """
        if queryset.count() != 1:
            self.message_user(request, _("Please select exactly one tenant."), messages.ERROR)
            return None
        return redirect("admin:tenants_tenant_assign_devices", queryset.get().pk)

    def get_urls(self):
        custom_urls = [
            path(
                "<int:tenant_id>/assign-devices/",
                self.admin_site.admin_view(self.assign_devices_view),
                name="tenants_tenant_assign_devices",
            ),
        ]
        return custom_urls + super().get_urls()

    def assign_devices_view(self, request, tenant_id):
        if not self.has_assign_devices_permission(request):
            raise PermissionDenied
        tenant = get_object_or_404(Tenant, pk=tenant_id)
        # Same queryset as the "devices without tenant" hint (core.context_processors.hints).
        devices = Device.objects.filter(tenant__isnull=True)

        if request.method == "POST":
            # Only the confirmed devices that still have no tenant: a crafted pk
            # of a device with a tenant matches nothing.
            confirmed = list(devices.filter(pk__in=request.POST.getlist("device")))
            with transaction.atomic():
                # One save per device (not .update()), so simple-history and the
                # audit fields record the change.
                for device in confirmed:
                    device.tenant = tenant
                    device.user, device.username = get_denormalized_user(request.user)
                    device.save()

            self.message_user(
                request,
                ngettext(
                    "%(count)d device assigned to tenant “%(tenant)s”.",
                    "%(count)d devices assigned to tenant “%(tenant)s”.",
                    len(confirmed),
                )
                % {"count": len(confirmed), "tenant": tenant},
                messages.SUCCESS if confirmed else messages.WARNING,
            )
            return redirect("admin:tenants_tenant_changelist")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": _("Assign devices without tenant"),
            "tenant": tenant,
            "devices": devices.select_related("device_type", "active_record__room").order_by("pk"),
        }
        return TemplateResponse(request, "tenants/actions/assign_devices.html", context)
