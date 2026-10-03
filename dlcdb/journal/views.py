# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The journal in the frontend: a read-only list and detail of its entries."""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_GET

from dlcdb.theme.filterbar import build_filterbar
from dlcdb.theme.navigation import index_url
from dlcdb.theme.pagination import paginate

from . import cleanup
from .filters import JournalEntryFilter
from .forms import AGE_CHOICES, RemoveOldEntriesForm
from .models import JournalEntry

ENTRIES_PER_PAGE = 50


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
    base_queryset = JournalEntry.objects.visible_to(request.tenants)

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
    visible = JournalEntry.objects.visible_to(request.tenants)
    entry = get_object_or_404(visible.select_related("tenant", "content_type"), pk=pk)
    context = {
        "entry": entry,
        "subject_url": _subject_url(entry),
        "index_url": index_url(request, "journal:index"),
    }
    return TemplateResponse(request, "journal/detail.html", context)


@permission_required("journal.delete_journalentry", raise_exception=True)
def journal_cleanup(request):
    """
    Confirm, then remove: repeated HR sync runs and anomalies (keeping the first
    and the latest of each group), or the entries older than a number of months.
    Only entries the user can see are removed by age.
    """
    visible = JournalEntry.objects.visible_to(request.tenants)
    now = timezone.now()
    form = RemoveOldEntriesForm(request.POST or None)

    if request.method == "POST":
        if request.POST.get("action") == "repeats":
            count = cleanup.remove_repeats(user=request.user)
            messages.success(
                request,
                ngettext("Removed %(count)d repeated entry.", "Removed %(count)d repeated entries.", count)
                % {"count": count},
            )
            return redirect("journal:index")
        if form.is_valid():
            cutoff = cleanup.months_before(now, form.cleaned_data["months"])
            count = cleanup.remove_older_than(visible, cutoff, user=request.user)
            messages.success(
                request,
                ngettext(
                    "Removed %(count)d entry older than %(date)s.",
                    "Removed %(count)d entries older than %(date)s.",
                    count,
                )
                % {"count": count, "date": date_format(cutoff, "SHORT_DATE_FORMAT")},
            )
            return redirect("journal:index")

    groups = cleanup.repeat_groups()
    age_options = []
    for months in AGE_CHOICES:
        cutoff = cleanup.months_before(now, months)
        age_options.append({"months": months, "cutoff": cutoff, "count": visible.filter(timestamp__lt=cutoff).count()})

    context = {
        "groups": groups,
        "repeat_count": sum(len(group.removable) for group in groups),
        "age_options": age_options,
        "form": form,
        "index_url": reverse("journal:index"),
    }
    return TemplateResponse(request, "journal/cleanup.html", context)
