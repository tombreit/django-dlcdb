from django.contrib import admin
from django.db import models
from django.forms import Textarea

from .models import LendingConfiguration


@admin.register(LendingConfiguration)
class LendingConfigurationAdmin(admin.ModelAdmin):

    search_fields = [
        'lending_preparation_checklist',
    ]

    formfield_overrides = {
        models.TextField: {
            'widget': Textarea(
                attrs={
                    'style': 'width: 100%;'
                }
            )
        },
    }

    fieldsets = (
        ('Printouts', {
            'classes': ('collapse',),
            'fields': (
                'lending_preparation_checklist',
            ),
        }),
    )

    class Media:
        css = { "all": ("lending/admin/lending_admin.css",)}
