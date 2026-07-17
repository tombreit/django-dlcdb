# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Frontend views for the two-step device import: upload + dry run, preview,
explicit confirm. The import logic itself lives in importer.run_device_import
and is shared with the admin importer.
"""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .csv_template import build_import_template_csv
from .forms import DeviceImportForm
from .importer import run_device_import
from .models import ImporterList
from .reporting import Outcome


OUTCOME_BADGES = {
    Outcome.CREATED: "text-bg-success",
    Outcome.UPDATED: "text-bg-info",
    Outcome.UNCHANGED: "text-bg-light border",
    Outcome.SKIPPED: "text-bg-warning",
    Outcome.REMOVED: "text-bg-secondary",
    Outcome.ERROR: "text-bg-danger",
}

ALERT_BY_LEVEL = {
    "success": "alert-success",
    "warning": "alert-warning",
    "error": "alert-danger",
}


def _report_context(report):
    """Prepare an OperationReport as plain template-ready data."""
    return {
        "summary": report.counts_summary(),
        "alert_class": ALERT_BY_LEVEL[report.level],
        "counts": [
            {"outcome": outcome.value, "count": count, "badge": OUTCOME_BADGES[outcome]}
            for outcome, count in report.counts.items()
            if count
        ],
        "rows": [
            {
                "row": row.row,
                "identifier": row.identifier,
                "outcome": row.outcome.value,
                "badge": OUTCOME_BADGES[row.outcome],
                "detail": row.detail,
            }
            for row in report.rows
        ],
    }


@permission_required("core.add_device", raise_exception=True)
def device_import(request):
    """Step 1: upload a CSV, dry-run it and show the preview; nothing is written."""
    form = DeviceImportForm(request.POST or None, request.FILES or None, request=request)

    if request.method == "POST" and form.is_valid():
        importer_list = form.save(commit=False)
        if not request.user.is_superuser:
            importer_list.tenant = getattr(request, "tenant", None)
        # Archive the file and create the audit row up front: failed attempts
        # are part of the import history (run_device_import marks the row with
        # status "error"); status stays empty until a confirmed write.
        importer_list.save()
        try:
            report = run_device_import(
                file=form.cleaned_data["file"],
                tenant=importer_list.tenant,
                import_format=importer_list.import_format,
                username=request.user.username,
                importer_list=importer_list,
                write=False,
            )
        except ValidationError as error:
            form.add_error("file", error)
        except (ValueError, IntegrityError) as error:
            form.add_error("file", str(error))
        else:
            context = {
                "title": _("Import preview"),
                "importer_list": importer_list,
                "report": _report_context(report),
                "can_confirm": bool(report.rows),
            }
            return TemplateResponse(request, "dataexchange/import_preview.html", context)

    context = {
        "title": _("Import devices"),
        "form": form,
        "valid_col_headers": ImporterList.VALID_COL_HEADERS,
    }
    return TemplateResponse(request, "dataexchange/import.html", context)


@require_POST
@permission_required("core.add_device", raise_exception=True)
def device_import_confirm(request, pk):
    """Step 2: write the previously uploaded and previewed file for real."""
    queryset = ImporterList.objects.all()
    if not request.user.is_superuser:
        queryset = queryset.filter(tenant=getattr(request, "tenant", None))
    importer_list = get_object_or_404(queryset, pk=pk)

    # persist() sets a success/warning status only on a real write, so it means
    # this file has already been imported (e.g. a re-posted confirm form).
    # An "error" status marks a failed attempt whose write rolled back, so it
    # may be retried.
    if importer_list.status in (ImporterList.Status.SUCCESS, ImporterList.Status.WARNING):
        messages.warning(request, _("This import file has already been processed."))
        return redirect("assets:device_index")

    try:
        report = run_device_import(
            file=importer_list.file,
            tenant=importer_list.tenant,
            import_format=importer_list.import_format,
            username=request.user.username,
            importer_list=importer_list,
            write=True,
        )
    except (ValidationError, ValueError, IntegrityError) as error:
        messages.error(request, _("Import failed, nothing was written: %(error)s") % {"error": error})
        return redirect("dataexchange:device_import")

    getattr(messages, report.level)(request, report.short_html())
    return redirect("assets:device_index")


@permission_required("core.add_device", raise_exception=True)
def device_import_template(request):
    """Header-only CSV template with all importable columns."""
    response = HttpResponse(build_import_template_csv(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="dlcdb-device-import-template.csv"'
    return response
