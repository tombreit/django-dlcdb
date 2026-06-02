# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.contrib import messages
from django.db import IntegrityError

from .importer import import_data
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
            report_dryrun = import_data(
                file,
                importer_inst_pk=None,
                valid_col_headers=self.instance.VALID_COL_HEADERS,
                import_format=import_format,
                tenant=tenant,
                username=username,
                write=False,
            )
        except (ValueError, IntegrityError) as error:
            self.add_error(None, error)
        else:
            _show_report(self.request, report_dryrun)


class RemoverListAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        username = self.request.user.username

        # Fail loudly: any error raised by set_removed_record propagates.
        report_dryrun = set_removed_record(file, username=username, write=False)
        _show_report(self.request, report_dryrun)
