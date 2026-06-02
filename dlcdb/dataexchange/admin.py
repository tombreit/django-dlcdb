# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.contrib import messages

from .models import ImporterList, RemoverList
from .forms import ImporterAdminForm, RemoverListAdminForm
from .importer import import_data
from .remover import set_removed_record


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
                "fields": (
                    "import_format",
                    "tenant",
                ),
            },
        ),
        (
            "Metadata",
            {
                "classes": ("collapse",),
                "fields": (
                    "messages",
                    "created_at",
                    "modified_at",
                ),
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
        report = import_data(
            obj.file,
            importer_inst_pk=obj.pk,
            valid_col_headers=obj.VALID_COL_HEADERS,
            import_format=obj.import_format,
            tenant=obj.tenant,
            username=request.user.username,
            write=True,
        )
        obj.messages = report.detailed()
        obj.save()
        getattr(messages, report.level)(request, report.short_html())


@admin.register(RemoverList)
class RemoverListAdmin(admin.ModelAdmin):
    form = RemoverListAdminForm

    fields = (
        "file",
        "note",
        "messages",
        "created_at",
        "modified_at",
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
        report = set_removed_record(
            obj.file,
            username=request.user.username,
            write=True,
        )
        obj.messages = report.detailed()
        obj.save()
        getattr(messages, report.level)(request, report.short_html())
