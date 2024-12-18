# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin

from .models import Branding


@admin.register(Branding)
class BrandingAdmin(admin.ModelAdmin):
    list_display = ("organization_name_en",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("organization_name_en", "organization_name_de"),
                    "organization_url",
                    "organization_abbr",
                )
            },
        ),
        (
            "Address",
            {
                "classes": ("collapse",),
                "fields": (
                    "organization_street",
                    "organization_zip_code",
                    "organization_city",
                ),
            },
        ),
        (
            "Logos",
            {
                "classes": ("collapse",),
                "fields": (
                    "organization_logo_white",
                    "organization_logo_black",
                    "organization_figurative_mark",
                    "organization_favicon",
                    "licenses_logo",
                ),
            },
        ),
        (
            "IT Department",
            {
                "classes": ("collapse",),
                "fields": (
                    "organization_it_dept_name",
                    "organization_it_dept_phone",
                    "organization_it_dept_email",
                ),
            },
        ),
        (
            "Misc",
            {
                "classes": ("collapse",),
                "fields": (
                    "documentation_url",
                    "room_plan",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        has_add_permisson = super().has_add_permission(request)
        if has_add_permisson and Branding.objects.exists():
            has_add_permisson = False
        return has_add_permisson
