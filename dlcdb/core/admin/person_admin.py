# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2


from django.contrib import admin
from django.utils.safestring import mark_safe

from .base_admin import SoftDeleteModelAdmin, CustomBaseModelAdmin
from ..models import Person, OrganizationalUnit


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(CustomBaseModelAdmin):
    list_display = [
        "name",
        "slug",
    ]

    prepopulated_fields = {"slug": ("name",)}


@admin.register(Person)
class PersonAdmin(SoftDeleteModelAdmin, CustomBaseModelAdmin):
    udb_fields = [
        "udb_person_last_name",
        "udb_person_first_name",
        "udb_person_email_private",
        "udb_person_email_internal_business",
        "udb_contract_planned_checkin",
        "udb_contract_planned_checkout",
        "udb_contract_organization_unit",
        "udb_contract_contract_type",
        "udb_contract_organizational_positions",
        "udb_person_image",
        "udb_person_uuid",
        "udb_data_updated_at",
    ]

    _readonly_fields = udb_fields
    _readonly_fields.append("udb_person_image_as_image")
    readonly_fields = _readonly_fields

    dlcdb_fields = [
        "last_name",
        "first_name",
        "email",
        "organizational_unit",
    ]

    dlcdb_deletion_fields = [
        "deleted_at",
        "deleted_by",
    ]

    search_fields = [
        "last_name",
        "first_name",
        "email",
        "udb_person_uuid",
        "udb_person_last_name",
        "udb_person_first_name",
        "udb_person_email_internal_business",
    ]

    list_display = [
        "last_name",
        "first_name",
        "email",
        "udb_person_email_internal_business",
        "organizational_unit",
        "udb_person_image_as_image",
        "deleted_at",
    ]

    list_filter = [
        "organizational_unit",
    ]

    fieldsets = (
        ("Person", {"fields": (*dlcdb_fields,)}),
        (
            "Misc",
            {
                "classes": ("collapse",),
                "fields": (*dlcdb_deletion_fields,),
            },
        ),
        (
            "UDB data",
            {
                "classes": ("collapse",),
                "fields": (*udb_fields,),
            },
        ),
    )

    def udb_person_image_as_image(self, obj):
        return mark_safe(
            '<img src="{url}" style="max-width: 100px;">'.format(
                url=obj.udb_person_image.url if obj.udb_person_image else "",
            )
        )

    udb_person_image_as_image.short_description = "Image"


#     def get_search_results(self, request, queryset, search_term):
#         print("In get search results")
#         results = super().get_search_results(request, queryset, search_term)
#         print(results)
#         return results

#     def get_urls(self):
#         print("get_urls...")
#         return [
#             path('autocomplete/', PersonAutocompleteJsonView.as_view(admin_site=self), name='customers_customer_autocomplete')
#             if url.pattern.match('autocomplete/')
#             else url for url in super().get_urls()
#         ]

# class PersonAutocompleteJsonView(AutocompleteJsonView):
#     def serialize_result(self, obj, to_field_name):
#         return super.serialize_result(obj, to_field_name) | {'notes': obj.notes}
