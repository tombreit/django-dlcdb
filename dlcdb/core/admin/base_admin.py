from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse

from ..utils.helpers import get_denormalized_user



class CustomBaseModelAdmin(admin.ModelAdmin):
    """
    Base class for all admins which should track request.user.
    """

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False

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


    def get_queryset(self, request):
        try:
            queryset = self.model.all_objects.all()
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
        return False

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
