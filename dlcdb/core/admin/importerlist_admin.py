# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..utils.bulk_management import import_data
from ..models import ImporterList
from ..forms.importer_admin_form import ImporterAdminForm


@admin.register(ImporterList)
class ImporterListAdmin(admin.ModelAdmin):
    form = ImporterAdminForm

    DATE_FIELDS = [
        "PURCHASE_DATE",
        "WARRANTY_EXPIRATION_DATE",
        "CONTRACT_EXPIRATION_DATE",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "file",
                    "note",
                )
            },
        ),
        (
            "Import (specified)",
            {
                "classes": ("collapse",),
                "fields": (
                    "import_format",
                    "tenant",
                ),
            },
        ),
        (
            None,
            {
                "fields": (
                    "messages",
                    "created_at",
                    "modified_at",
                )
            },
        ),
    )

    readonly_fields = (
        "messages",
        "created_at",
        "modified_at",
    )

    list_display = [
        "get_change_link_display",
        "created_at",
        "modified_at",
        "note",
    ]

    @admin.display(description="CSV-Datei")
    def get_change_link_display(self, obj):
        return "{label}".format(label=obj.file)

    def get_form(self, request, obj=None, **kwargs):
        """
        Add request context to form to display Django messages framework
        messages in form clean().
        """
        form = super().get_form(request, obj=obj, **kwargs)
        form.request = request
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # We only have a primary key for this object after saving
        result = import_data(
            obj.file,
            importer_inst_pk=obj.pk,
            valid_col_headers=obj.VALID_COL_HEADERS,
            import_format=obj.import_format,
            tenant=obj.tenant,
            username=request.user.username,
            write=True,
        )
        plaintext_messages = [
            result.imported_devices_count,
            "\n".join(result.success_messages),
        ]
        html_messages = format_html(
            "{}<br>{}<br>",
            result.imported_devices_count,
            mark_safe("<br>".join(result.success_messages)),
        )
        obj.messages = "\n".join(plaintext_messages)
        obj.save()
        messages.success(request, html_messages)
