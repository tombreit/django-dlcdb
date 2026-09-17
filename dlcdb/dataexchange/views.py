# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Frontend views for the two-step device import: upload + dry run, preview,
explicit confirm. The import logic itself lives in importer.run_device_import
and is shared with the admin importer.

Plus the read-only import history: an import is a one-off operation, so its
list and detail pages offer no edit, delete or re-run.
"""

import datetime

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from dlcdb.core.utils.tenants import tenant_scoped_queryset
from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.pagination import paginate

from .csv_template import build_import_template_csv
from .filters import ImporterListFilter
from .forms import DeviceImportForm
from .importer import IMPORT_ERRORS, import_error_message, run_device_import
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

IMPORTS_PER_PAGE = 25

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
        "error_count": report.counts[Outcome.ERROR],
        "has_errors": bool(report.counts[Outcome.ERROR]),
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
            for row in report.rows_in_file_order
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
        except IMPORT_ERRORS as error:
            form.add_error("file", import_error_message(error))
        else:
            context = {
                "title": _("Import preview"),
                "importer_list": importer_list,
                "report": _report_context(report),
                # Never offer to write a file that still has bad rows.
                "can_confirm": bool(report.rows) and not report.counts[Outcome.ERROR],
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
    except IMPORT_ERRORS as error:
        messages.error(
            request, _("Import failed, nothing was written: %(error)s") % {"error": import_error_message(error)}
        )
        return redirect("dataexchange:device_import")

    getattr(messages, report.level)(request, report.short_html())
    return redirect("assets:device_index")


@permission_required("core.add_device", raise_exception=True)
def device_import_template(request):
    """Header-only CSV template with all importable columns."""
    response = HttpResponse(build_import_template_csv(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="dlcdb-device-import-template.csv"'
    return response


def _importer_list_queryset(request):
    """Imports visible in the frontend, each with the count of devices it created."""
    queryset = ImporterList.objects.select_related("tenant").annotate(devices_count=Count("device", distinct=True))
    return tenant_scoped_queryset(queryset, request, tenant_field="tenant")


@permission_required("dataexchange.view_importerlist", raise_exception=True)
def importer_index(request):
    """Read-only, tenant-scoped import history."""
    template = "dataexchange/importer_index.html#importer-list" if request.htmx else "dataexchange/importer_index.html"
    base_queryset = _importer_list_queryset(request)

    data = request.GET.copy()
    data.setdefault("ordering", "-created")
    importer_filter = ImporterListFilter(data, queryset=base_queryset, request=request)

    page_obj = paginate(request, importer_filter.qs, IMPORTS_PER_PAGE)

    context = {
        "filter": importer_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            importer_filter,
            request,
            target="#importer-list",
            search_placeholder=_("Search file name, note..."),
        ),
        "current_ordering": data["ordering"],
        "filtered_count": page_obj.paginator.count,
        "total_count": base_queryset.count(),
        # Mirrors assets.views.devices.device_index, for theme/includes/_timestamps.html.
        "recent_cutoff": timezone.now() - datetime.timedelta(weeks=3),
    }
    return TemplateResponse(request, template, context)


@require_GET
@permission_required("dataexchange.view_importerlist", raise_exception=True)
def importer_detail(request, pk):
    """One import with its stored log. Read-only: there is nothing to change after the fact."""
    importer_list = get_object_or_404(_importer_list_queryset(request), pk=pk)

    # The index threads its active search/filter/sort here as ?next=.
    next_query = request.GET.get("next", "")
    index_url = reverse("dataexchange:importer_index")
    if next_query:
        index_url = f"{index_url}?{next_query}"

    context = {
        "importer_list": importer_list,
        "index_url": index_url,
        "devices_url": f"{reverse('assets:device_index')}?imported_by={importer_list.pk}",
    }
    return TemplateResponse(request, "dataexchange/importer_detail.html", context)
