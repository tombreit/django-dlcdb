from django.contrib import admin

from .models import Branding


@admin.register(Branding)
class BrandingAdmin(admin.ModelAdmin):
    list_display = ('organization_name_en',)

    fieldsets = (
        (None, {
            'fields': (
                ('organization_name_en', 'organization_name_de'),
                'organization_url', 'organization_abbr',
            )
        }),
        ('Address', {
            'classes': ('collapse',),
            'fields': (
                'organization_street',
                'organization_zip_code',
                'organization_city',
            ),
        }),
        ('Logos', {
            'classes': ('collapse',),
            'fields': (
                'organization_logo_white',
                'organization_logo_black',
                'organization_figurative_mark',
                'organization_favicon'
            ),
        }),
        ('IT Department', {
            'classes': ('collapse',),
            'fields': (
                'organization_it_dept_name',
                'organization_it_dept_phone',
                'organization_it_dept_email',
            ),
        }),
    )