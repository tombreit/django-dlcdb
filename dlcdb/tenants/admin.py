"""
https://fueled.com/the-cache/posts/backend/django/flexible-per-object-permission-system/
"""

from django.contrib import admin

from ..core.models import Device
from .models import Tenant


# class TenantModelAdmin(admin.ModelAdmin):

#     def has_change_permission(self, request, obj=None):
#         """
#         Return True if the given request has permission to change the given
#         Django model instance, the default implementation doesn't examine the
#         `obj` parameter.

#         Can be overridden by the user in subclasses. In such case it should
#         return True if the given request has permission to change the `obj`
#         model instance. If `obj` is None, this should return True if the given
#         request has permission to change *any* object of the given type.
#         """
#         opts = self.opts
#         codename = get_permission_codename('change', opts)
#         return request.user.has_perm("%s.%s" % (opts.app_label, codename))

#     def has_delete_permission(self, request, obj=None):
#         """
#         Return True if the given request has permission to change the given
#         Django model instance, the default implementation doesn't examine the
#         `obj` parameter.

#         Can be overridden by the user in subclasses. In such case it should
#         return True if the given request has permission to delete the `obj`
#         model instance. If `obj` is None, this should return True if the given
#         request has permission to delete *any* object of the given type.
#         """
#         opts = self.opts
#         codename = get_permission_codename('delete', opts)
#         return request.user.has_perm("%s.%s" % (opts.app_label, codename))

#     def has_view_permission(self, request, obj=None):
#         """
#         Return True if the given request has permission to view the given
#         Django model instance. The default implementation doesn't examine the
#         `obj` parameter.

#         If overridden by the user in subclasses, it should return True if the
#         given request has permission to view the `obj` model instance. If `obj`
#         is None, it should return True if the request has permission to view
#         any object of the given type.
#         """

#         print(f"has_view_permission: {obj=}")

#         opts = self.opts
#         codename_view = get_permission_codename('view', opts)
#         print(f"{codename_view=}")
#         codename_change = get_permission_codename('change', opts)
#         return (
#             request.user.has_perm('%s.%s' % (opts.app_label, codename_view)) or
#             request.user.has_perm('%s.%s' % (opts.app_label, codename_change))
#         )

#     def has_view_or_change_permission(self, request, obj=None):
#         return self.has_view_permission(request, obj) or self.has_change_permission(request, obj)


class TenantScopedAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return super().get_readonly_fields(request, obj) + (
                "tenant",
            )
        else:
            return super().get_readonly_fields(request, obj)

    # def get_changeform_initial_data(self, request):
    #     return {'tenant': request.tenant}

    def get_queryset(self, request):
        """
        Return a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """

        # print(f"TenantModelAdmin get_queryset {request.user.username=}")
        # print(f"TenantModelAdmin get_queryset {request.tenant=}")
        # print(f"{dir(self.model)=}")

        # Set an empty queryset as default
        qs = super().get_queryset(request).none()

        if request.user.is_superuser:
            # No pre-filtering for superusers
            qs = super().get_queryset(request)

        if not request.tenant:
            # print("We have no tenant, returning an empty queryset")
            qs = qs
        else:
            qs = super().get_queryset(request)

            if self.model is Device:
                qs = qs.filter(tenant=request.tenant)
            else:
                """
                We're interacting with a record or proxy record class.
                As we do not track the tenant id on the record class
                yet, we filter against the device tenant.
                """
                qs = qs.filter(device__tenant=request.tenant)

        return qs

    def get_form(self, request, obj=None, change=False, **kwargs):
        """
        Setting default tenant value for new admin forms and make them readonly.
        Using `readonly_fields = ('tenant',)` does not work as I do not know
        how to set a default value for these readonly_fields.
        """
        form = super().get_form(request, obj=None, change=False, **kwargs)

        # print(f"TenantScopedAdmin get_form: {request.tenant=}")
        # print(f"TenantScopedAdmin form.base_fields: {form.base_fields=}")

        if form.base_fields.get('tenant'):
            form.base_fields['tenant'].disabled = False if request.user.is_superuser else True
        
        if not obj:
            if not request.user.is_superuser and request.tenant:
                # If field value set via get_changeform_initial_data this value
                # will not be present in the post request, so we set it
                # in the form:
                if form.base_fields.get('tenant'):
                    form.base_fields['tenant'].initial = request.tenant

        return form

    def save_model(self, request, obj, form, change):
        """
        Ensure tenant is set according to request.tenant
        """
        if not request.user.is_superuser:
            obj.tenant = request.tenant

        super().save_model(request, obj, form, change)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('groups',)
