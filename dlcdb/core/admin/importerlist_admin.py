from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..utils.bulk_management import import_data
from ..models import ImporterList
from ..forms.importer_admin_form import ImporterAdminForm


@admin.register(ImporterList)
class ImporterListAdmin(admin.ModelAdmin):
    form = ImporterAdminForm

    DATE_FIELDS = [
        'PURCHASE_DATE',
        'WARRANTY_EXPIRATION_DATE',
        'MAINTENANCE_CONTRACT_EXPIRATION_DATE',
    ]

    fields = (
        'file',
        'note',
        'messages',
        'created_at',
        'modified_at',
    )

    readonly_fields = (
        'messages',
        'created_at',
        'modified_at',
    )

    list_display = [
        'get_change_link_display',
        'created_at',
        'modified_at',
        'note',
    ]

    @admin.display(description='CSV-Datei')
    def get_change_link_display(self, obj):
        return '{label}'.format(label=obj.file)

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
        try:
            result = import_data(obj.file, importer_inst_pk=obj.pk, write=True)
            plaintext_messages = [
                result.imported_devices_count,
                result.processed_rows_count,
                "\n".join(result.success_messages),
            ]
            html_messages = format_html("{}<br>{}<br>{}",
                result.imported_devices_count,
                result.processed_rows_count,
                mark_safe("<br>".join(result.success_messages)),
            )
            obj.messages = "\n".join(plaintext_messages)
            obj.save()
            messages.success(request, html_messages)
        except BaseException as base_exception:
            # This should never happen, as we validated the file in a dry-run
            # for this import file in the modelforms clean method.
            raise ValidationError(base_exception)
