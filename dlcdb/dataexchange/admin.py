# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.contrib import admin
from django.contrib import messages

from dlcdb.core.models import Device, LentRecord

from .models import ImporterList, RemoverList, UdbSyncConfiguration, UdbSyncRun
from .forms import ImporterAdminForm, RemoverListAdminForm
from .importer import run_device_import
from .remover import set_removed_record
from .device_export import EXPORT_RELATIONS, device_csv_response


class ExportCsvMixin:
    """Changelist action exporting the selected devices as CSV.

    Mixed into ``core.admin.DeviceAdmin`` and ``core.admin.LentRecordAdmin``.
    Rows are built in ``device_export``, which the assets frontend export shares,
    so both surfaces emit the same file.
    """

    @admin.action(description="Export selected as CSV")
    def export_as_csv(self, request, queryset):
        meta = self.model._meta

        if meta.model is LentRecord:
            # The action hangs off the LentRecord changelist but exports the
            # devices behind the selected records. No extra columns needed: the
            # borrower and the lending dates are part of every device row.
            devices = Device.objects.filter(pk__in=queryset.values_list("device", flat=True))
        else:
            devices = queryset

        # The changelist queryset joins only what the changelist renders; the
        # export reads more relations than that.
        devices = devices.select_related(*EXPORT_RELATIONS)

        return device_csv_response(devices, slug=f"{meta.app_label}-{meta.model_name}")


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
        report = run_device_import(
            file=obj.file,
            tenant=obj.tenant,
            import_format=obj.import_format,
            username=request.user.username,
            importer_list=obj,
            write=True,
        )
        getattr(messages, report.level)(request, report.short_html())


class UdbSyncConfigurationForm(forms.ModelForm):
    class Meta:
        model = UdbSyncConfiguration
        fields = "__all__"
        widgets = {
            # Mask the token in the admin form. `render_value` keeps the stored
            # value on edit so saving the form does not wipe it.
            "api_token": forms.PasswordInput(render_value=True),
        }


@admin.register(UdbSyncConfiguration)
class UdbSyncConfigurationAdmin(admin.ModelAdmin):
    form = UdbSyncConfigurationForm
    actions = ["sync_now"]

    def has_add_permission(self, request):
        return not UdbSyncConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Run HR API sync now")
    def sync_now(self, request, queryset):
        # Enqueue the relocated huey task; imported lazily to avoid loading the
        # task module (and huey) at admin import time.
        from .tasks import task_import_udb_persons

        task_import_udb_persons()
        messages.info(request, "HR API sync has been enqueued. See the 'HR API Sync Runs' list for the result.")


@admin.register(UdbSyncRun)
class UdbSyncRunAdmin(admin.ModelAdmin):
    list_display = ["created_at", "status", "summary"]
    list_filter = ["status"]
    readonly_fields = ["status", "summary", "messages", "created_at", "modified_at"]

    def has_add_permission(self, request):
        # Runs are created by the sync, never by hand.
        return False


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
        report.persist(obj)
        getattr(messages, report.level)(request, report.short_html())
