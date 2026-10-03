# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import date

from django.apps import apps
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from dlcdb.core.models import Inventory, LentRecord, Record
from dlcdb.core.utils.helpers import get_icon_for_class
from dlcdb.core.utils.htmx import htmx_login_required
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.shortcuts import tenant_scoped_queryset

from . import stats
from .search import run_search

# GET parameter carrying the global search term.
GLOBAL_SEARCH_PARAM = "q"

# How far back the journal tile counts problems.
JOURNAL_TILE_DAYS = 30


# Map each dashboard model to the field path used to scope its queryset to a
# tenant.
TENANT_FILTERS = {
    "core.device": "tenant",
    "core.lentrecord": "device__tenant",
    "core.lostrecord": "device__tenant",
    "core.licencerecord": "device__tenant",
    "core.room": "record__device__tenant",
    "core.devicetype": "device__tenant",
}
# Models that need .distinct() due to joins through intermediary tables.
TENANT_DISTINCT = {"core.room", "core.devicetype"}

# Tiles whose note badge is intentionally not shown (kept for parity with the
# admin dashboard, where these counts can be large/noisy).
NO_BADGE_MODELS = {"core.device", "core.lentrecord", "core.licencerecord"}


def _get_tenant_queryset(model_name, ModelClass, request):
    filter_field = TENANT_FILTERS.get(model_name)
    if filter_field is None:
        # Not tenant-aware (e.g. inventories, smallstuff).
        return ModelClass.objects.all()

    # Distinctness is applied in _build_tile via Count(distinct=...), not here,
    # so it is expressed once at the aggregation.
    return tenant_scoped_queryset(ModelClass.objects.all(), request, tenant_field=filter_field)


def _build_tile(*, model_name, url, request, base_params=None):
    """Build the context dict for a single dashboard tile.

    ``base_params`` are the GET parameters the tile's target needs to show the
    same set the tile counts (e.g. the Lost tile scoping the record list to
    LOST). The note filter is appended to them when the badge is shown.
    """
    ModelClass = apps.get_model(model_name)
    qs = _get_tenant_queryset(model_name, ModelClass, request)

    # Collapse the per-tile counts (total, note badge, lent) into a single
    # aggregate query instead of 2-3 separate .count() scans over the same rows.
    distinct = model_name in TENANT_DISTINCT
    agg = {"total": Count("pk", distinct=distinct)}
    if hasattr(ModelClass, "note"):
        agg["with_note"] = Count("pk", filter=~Q(note__exact=""), distinct=distinct)
    if model_name == "core.lentrecord":
        agg["lent"] = Count("pk", filter=Q(record_type=Record.LENT), distinct=distinct)

    counts = qs.aggregate(**agg)
    raw_count = counts["total"]
    note_count = counts.get("with_note", 0)
    human_name = ModelClass._meta.verbose_name_plural if raw_count >= 2 else ModelClass._meta.verbose_name

    count = raw_count
    if model_name == "core.lentrecord":
        count = f"{counts['lent']} / {raw_count}"
    elif model_name == "core.inventory":
        count = ModelClass.objects.filter(is_active=True).first()

    show_badge = bool(note_count) and model_name not in NO_BADGE_MODELS

    # Keyed off show_badge, not note_count: a tile whose badge is suppressed must
    # not link to a note-filtered list either, or the link promises a filter the
    # tile never advertised.
    params = dict(base_params or {})
    if show_badge:
        params["has_note"] = "has_note"

    return {
        "label": human_name,
        "count": count,
        "note_count": note_count,
        "show_badge": show_badge,
        "icon": get_icon_for_class(model_name),
        "url": url,
        "query_params": urlencode(params),
    }


@htmx_login_required
def index(request):
    """
    Dashboard on the theme frontend: model tiles (counts + note badges) and
    Plotly stats, scoped to the user's tenants, plus the global search.

    Search results are served from this same URL so that ``hx-push-url`` puts
    ``/dashboard/?q=…`` in the address bar: a search is then shareable and
    bookmarkable, and reloading it renders the very same page server-side. HTMX
    gets only the results fragment -- the tile aggregates and the three Plotly
    figures are far too expensive to rebuild on every keystroke.

    Guarded HTMX-aware rather than with plain ``login_required``: on an expired
    session a 302 would otherwise swap the whole login page into the results
    panel. Per-source permissions are applied inside ``run_search``.
    """
    term = (request.GET.get(GLOBAL_SEARCH_PARAM) or "").strip()
    search_context = {
        "search_param": GLOBAL_SEARCH_PARAM,
        "search_term": term,
        "groups": run_search(request, term),
    }

    if request.htmx:
        return TemplateResponse(request, "dashboard/index.html#search-results", search_context)

    # (model, url name, GET params the target needs to show what the tile counts).
    # Every target is a frontend view: the tiles are the last place that linked
    # into the admin changelists the frontend apps have since replaced.
    tile_specs = [
        ("core.device", "assets:device_index", {}),
        ("core.lentrecord", "lending:index", {}),
        ("core.room", "rooms:index", {}),
        ("core.devicetype", "assets:device_type_index", {}),
        ("core.licencerecord", "licenses:index", {}),
        ("smallstuff.assignedthing", "smallstuff:person_search", {}),
        # LostRecord.objects is Record filtered to LOST with no is_active filter,
        # so the unfiltered-by-age record list under the same record_type matches
        # the count exactly.
        ("core.lostrecord", "assets:record_index", {"record_type": Record.LOST}),
    ]
    if Inventory.objects.filter(is_active=True).exists():
        tile_specs.append(("core.inventory", "inventory:inventorize-room-list", {}))

    # Deliberately not permission-filtered: every tile renders, and a user who
    # may not open its target gets the ordinary 403 on click.
    tiles = [
        _build_tile(model_name=name, url=url, request=request, base_params=params) for name, url, params in tile_specs
    ]

    # Overdue tile: same predicate as the lending list's "state=overdue" filter
    # (lending/filters.py), so the count always matches the linked list.
    overdue_qs = tenant_scoped_queryset(
        LentRecord.objects.filter(lent_desired_end_date__lte=date.today(), lent_end_date__isnull=True),
        request,
        tenant_field="device__tenant",
    )
    tiles.insert(
        2,
        {
            "label": _("Overdue lendings"),
            "count": overdue_qs.count(),
            "note_count": 0,
            "show_badge": False,
            "icon": "bi bi-alarm",
            "url": "lending:index",
            "query_params": "state=overdue",
        },
    )

    # Journal tile: one count per problem level instead of a single count. It
    # links to the whole journal; the period only applies to the counts.
    tiles.append(
        {
            "label": ngettext("Journal, last %(days)d day", "Journal, last %(days)d days", JOURNAL_TILE_DAYS)
            % {"days": JOURNAL_TILE_DAYS},
            "level_counts": JournalEntry.objects.problem_counts(tenants=request.tenants, days=JOURNAL_TILE_DAYS),
            "note_count": 0,
            "show_badge": False,
            "icon": "bi bi-journal-text",
            "url": "journal:index",
            "query_params": "",
        }
    )

    context = {
        "tiles": tiles,
        "record_fraction_html": stats.get_record_fraction_html(tenants=request.tenants),
        "device_type_html": stats.get_device_type_html(tenants=request.tenants),
        "record_timeline_html": stats.get_record_timeline_html(tenants=request.tenants),
        **search_context,
    }
    return TemplateResponse(request, "dashboard/index.html", context)
