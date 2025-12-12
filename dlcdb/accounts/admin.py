# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
TODO: Get rid of our custom delete() and hard_delete() methods.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.contrib.admin.utils import unquote
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages


from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = UserAdmin.list_display + ("is_active",)
    change_form_template = "accounts/customuser/change_form.html"

    # For now we still have to deal with the legacy username field
    # so we keep the default forms for now.
    # add_form = CustomUserCreationForm
    # form = CustomUserChangeForm

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/hard-delete/",
                self.admin_site.admin_view(self.hard_delete_view),
                name="accounts_customuser_hard_delete",
            ),
        ]
        return custom_urls + urls

    def hard_delete_view(self, request, object_id, extra_context=None):
        """
        Reuse Django's delete view but call hard_delete instead of delete
        """
        # Most of this is taken directly from ModelAdmin.delete_view
        opts = self.model._meta

        obj = self.get_object(request, unquote(object_id))
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        # The actual override: handle POST request to do hard delete
        if request.method == "POST":
            obj_display = str(obj)
            obj.hard_delete()  # This is the key difference - use hard_delete
            self.message_user(
                request,
                _('The %(name)s "%(obj)s" was permanently deleted.')
                % {
                    "name": opts.verbose_name,
                    "obj": obj_display,
                },
                level=messages.SUCCESS,
            )

            return HttpResponseRedirect(reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist"))

        # For displaying related objects, reuse Django's delete_view
        # This will show the same confirmation page as regular delete
        extra_context = extra_context or {}
        extra_context["title"] = _("Permanently delete %s") % opts.verbose_name

        # Extra context to customize the template
        extra_context["is_hard_delete"] = True

        # Return the regular delete view for confirmation page
        return super().delete_view(request, object_id, extra_context)

    class Media:
        js = ("accounts/js/defaultsorting.js",)


# Move the Django upstream "Group" admin in our "Account" admin section


class Group(DjangoGroup):
    """Instead of trying to get new user under existing `Aunthentication and Authorization`
    banner, create a proxy group model under our Accounts app label.
    Refer to: https://github.com/tmm/django-username-email/blob/master/cuser/admin.py
    """

    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")
        proxy = True


admin.site.unregister(DjangoGroup)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    pass
