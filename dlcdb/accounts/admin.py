from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = UserAdmin.list_display + (
        "is_active",
    )

    class Media:
        js = ('accounts/js/defaultsorting.js',)


admin.site.register(CustomUser, CustomUserAdmin)
