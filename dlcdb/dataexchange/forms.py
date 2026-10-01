# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from dlcdb.tenants.shortcuts import limit_tenant_field

from .importer import IMPORT_ERRORS, import_error_message, run_device_import
from .models import ImporterList
from .remover import set_removed_record


def _show_report(request, report):
    # Dry-run reports never carry the "error" level (hard errors raise instead).
    # Stay silent when the dry-run is fully clean — the real import's toast in
    # save_model() is the single source of truth for a successful run. Only surface
    # the dry-run when it has warnings (e.g. skipped rows) worth seeing pre-commit.
    if report.level == "success":
        return
    level = report.level if report.level != "error" else "warning"
    getattr(messages, level)(request, report.short_html())


class ImporterAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        tenant = cleaned_data.get("tenant")
        import_format = cleaned_data.get("import_format")
        username = self.request.user.username

        try:
            report_dryrun = run_device_import(
                file=file,
                tenant=tenant,
                import_format=import_format,
                username=username,
                write=False,
            )
        except IMPORT_ERRORS as error:
            self.add_error(None, import_error_message(error))
        else:
            _show_report(self.request, report_dryrun)


class DeviceImportForm(forms.ModelForm):
    """
    Frontend upload form for the two-step device import (dry run, then confirm).

    ``import_format`` is intentionally not a form field: the frontend only
    supports the internal CSV format, so the model default applies. SAP imports
    stay admin-only.
    """

    class Meta:
        model = ImporterList
        fields = ["file", "note", "tenant"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

        # The model help_text is the full column list as admin-oriented HTML;
        # the frontend page explains the columns itself.
        self.fields["file"].help_text = _("CSV file in the internal format (UTF-8).")
        self.fields["note"].label = _("Note")

        # Only the user's tenants are offered, so a crafted foreign tenant
        # fails validation. The field stays required (model blank=False):
        # imported devices without a tenant would be invisible to everyone.
        limit_tenant_field(self.fields["tenant"], request.tenants)

        # Bootstrap 5 control styling, mirroring the frontend DeviceForm.
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

        # Bootstrap 5 server-side validation styling: a bound field that failed
        # validation renders in the invalid state (red border + icon).
        if self.is_bound:
            for name in self.errors:
                field = self.fields.get(name)
                if field is None:
                    continue  # non-field ("__all__") errors
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} is-invalid".strip()


class RemoverListAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        username = self.request.user.username

        # Fail loudly: any error raised by set_removed_record propagates.
        report_dryrun = set_removed_record(file, username=username, write=False)
        _show_report(self.request, report_dryrun)
