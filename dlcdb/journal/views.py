# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The journal in the frontend: a read-only list and detail of its entries."""

from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.navigation import index_url
from dlcdb.theme.pagination import paginate

from .filters import JournalEntryFilter
from .models import JournalEntry

ENTRIES_PER_PAGE = 50


def _journal_queryset(request):
    """
    Entries of the request's tenants plus the tenant-less ones.

    Unlike ``tenant_scoped_queryset``, which never includes objects without a
    tenant: a tenant-less entry is not an orphan but a system event (an HR sync
    run, a logged error), and every journal viewer may see it.
    """
    return JournalEntry.objects.filter(Q(tenant__in=request.tenants) | Q(tenant__isnull=True))


def _subject_url(entry):
    """Link to the entry's subject, if it still exists and has a page of its own."""
    # A subject whose model is gone (a retired log table) has no model class.
    if entry.content_type is None or entry.content_type.model_class() is None:
        return ""
    get_absolute_url = getattr(entry.content_object, "get_absolute_url", None)
    # May return None for objects without a page (a Device unless it is a licence).
    return (get_absolute_url and get_absolute_url()) or ""


@permission_required("journal.view_journalentry", raise_exception=True)
def journal_index(request):
    """Read-only journal list, with progressive HTMX filtering."""
    template = "journal/index.html#journal-list" if request.htmx else "journal/index.html"
    base_queryset = _journal_queryset(request)

    data = request.GET.copy()
    data.setdefault("ordering", "-timestamp")
    journal_filter = JournalEntryFilter(data, queryset=base_queryset, request=request)

    page_obj = paginate(request, journal_filter.qs, ENTRIES_PER_PAGE)

    context = {
        "filter": journal_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            journal_filter,
            request,
            target="#journal-list",
            search_placeholder=_("Search summary, details, user..."),
        ),
        "current_ordering": data["ordering"],
        "filtered_count": page_obj.paginator.count,
        "total_count": base_queryset.count(),
    }
    return TemplateResponse(request, template, context)


@require_GET
@permission_required("journal.view_journalentry", raise_exception=True)
def journal_detail(request, pk):
    """One entry with its details. Entries are never changed, so nothing is editable."""
    entry = get_object_or_404(_journal_queryset(request).select_related("tenant", "content_type"), pk=pk)
    context = {
        "entry": entry,
        "subject_url": _subject_url(entry),
        "index_url": index_url(request, "journal:index"),
    }
    return TemplateResponse(request, "journal/detail.html", context)
