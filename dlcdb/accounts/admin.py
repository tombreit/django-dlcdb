# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = UserAdmin.list_display + ("is_active",)

    class Media:
        js = ("accounts/js/defaultsorting.js",)


admin.site.register(CustomUser, CustomUserAdmin)


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
