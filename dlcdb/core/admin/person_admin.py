from django.contrib import admin

from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin
from ..models import Person

@admin.register(Person)
class PersonAdmin(SoftDeleteModelAdmin, CustomBaseModelAdmin):

    udb_fields = [
        'udb_person_last_name',
        'udb_person_first_name',
        'udb_person_email_private',
        'udb_person_email_internal_business',
        'udb_contract_planned_checkin',
        'udb_contract_planned_checkout',
        'udb_contract_organization_unit',
        'udb_contract_contract_type',
        'udb_contract_organizational_positions',
        'udb_person_uuid',
        'udb_data_updated_at',
    ]

    readonly_fields = udb_fields

    dlcdb_fields = [
        'last_name',
        'first_name',
        'email',
        'department',
    ]

    search_fields = [
        'last_name',
        'first_name',
        'email',
        'udb_person_last_name',
        'udb_person_first_name',
        'udb_person_email_internal_business',
    ]

    list_display = [
        'last_name',
        'first_name',
        'email',
        'udb_person_email_internal_business',
        'department',
    ]

    list_filter = [
        'department'
    ]


    fieldsets = (
        ('Person', {
            'fields': (
                *dlcdb_fields,
            )
        }),
        ('UDB data', {
            'classes': ('collapse',),
            'fields': (
                *udb_fields,
            ),
        }),
    )
