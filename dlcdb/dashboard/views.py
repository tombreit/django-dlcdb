# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import apps
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from dlcdb.core.models import Inventory, LentRecord, Record
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.shortcuts import tenant_scoped_queryset
from dlcdb.theme.icons import get_icon_for_class

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

# Tiles whose note count is intentionally not shown (kept for parity with the
# admin dashboard, where these counts can be large/noisy).
NO_NOTES_MODELS = {"core.device", "core.lentrecord", "core.licencerecord"}


def _get_tenant_queryset(model_name, ModelClass, request):
    filter_field = TENANT_FILTERS.get(model_name)
    if filter_field is None:
        # Not tenant-aware (e.g. inventories, smallstuff).
        return ModelClass.objects.all()

    # Distinctness is applied in _build_tile via Count(distinct=...), not here,
    # so it is expressed once at the aggregation.
    return tenant_scoped_queryset(ModelClass.objects.all(), request, tenant_field=filter_field)


def _tile(*, label, value, icon, url, query_params="", **extra):
    """
    The context dict of one tile. Every tile has the same keys, so the
    template needs no ``default`` filters:

    - ``value``: the number the tile shows, ``unit`` an optional suffix ("%");
    - ``caption``: an optional line under it;
    - ``tone``: an optional Bootstrap colour name that tints the tile;
    - ``progress``: an optional percentage, drawn as a bar;
    - ``level_counts``: the journal tile's counts per level, instead of a value;
    - ``show_notes`` / ``note_count``: whether the caption reports notes.
    """
    return {
        "label": label,
        "value": value,
        "icon": icon,
        "url": url,
        "query_params": query_params,
        "unit": "",
        "caption": "",
        "tone": "",
        "progress": None,
        "level_counts": None,
        "show_notes": False,
        "note_count": 0,
        **extra,
    }


def _build_tile(*, model_name, url, request, base_params=None):
    """Build the context dict for a single model-count tile.

    ``base_params`` are the GET parameters the tile's target needs to show the
    same set the tile counts (e.g. the Lost tile scoping the record list to
    LOST). The note filter is appended to them when the note count is shown.
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
    total = counts["total"]
    note_count = counts.get("with_note", 0)

    value = total
    caption = ""
    if model_name == "core.lentrecord":
        # Lent devices, out of all lendable ones.
        value = counts["lent"]
        caption = _("of %(total)s lendable") % {"total": total}
    label = ModelClass._meta.verbose_name if value == 1 else ModelClass._meta.verbose_name_plural

    show_notes = bool(note_count) and model_name not in NO_NOTES_MODELS
    if show_notes:
        # Same msgid as the former badge's {% blocktranslate count %}.
        caption = ngettext("%(counter)s with note", "%(counter)s with notes", note_count) % {"counter": note_count}

    # Keyed off show_notes, not note_count: a tile whose note count is suppressed
    # must not link to a note-filtered list either, or the link promises a filter
    # the tile never advertised.
    params = dict(base_params or {})
    if show_notes:
        params["has_note"] = "has_note"

    return _tile(
        label=label,
        value=value,
        caption=caption,
        icon=get_icon_for_class(model_name),
        url=url,
        query_params=urlencode(params),
        show_notes=show_notes,
        note_count=note_count,
    )


def index(request):
    """
    Dashboard on the theme frontend: tiles in two groups (what needs attention,
    what is in stock) and Plotly stats, scoped to the user's tenants, plus the
    global search.

    Search results are served from this same URL so that ``hx-push-url`` puts
    ``/dashboard/?q=…`` in the address bar: a search is then shareable and
    bookmarkable, and reloading it renders the very same page server-side. HTMX
    gets only the results fragment -- the tile aggregates and the three Plotly
    figures are far too expensive to rebuild on every keystroke.

    Per-source permissions are applied inside ``run_search``.
    """
    term = (request.GET.get(GLOBAL_SEARCH_PARAM) or "").strip()
    search_context = {
        "search_param": GLOBAL_SEARCH_PARAM,
        "search_term": term,
        "groups": run_search(request, term),
    }

    if request.htmx:
        return TemplateResponse(request, "dashboard/index.html#search-results", search_context)

    # Every target is a frontend view: the tiles are the last place that linked
    # into the admin changelists the frontend apps have since replaced. Tiles are
    # deliberately not permission-filtered: every tile renders, and a user who may
    # not open its target gets the ordinary 403 on click.

    # Overdue lendings: LentRecord.objects.overdue(), like the lending list's
    # "state=overdue" filter it links to, so the count matches the list.
    overdue = tenant_scoped_queryset(LentRecord.objects.overdue(), request, tenant_field="device__tenant").count()
    attention_tiles = [
        _tile(
            label=_("Overdue lendings"),
            value=overdue,
            tone="warning" if overdue else "",
            icon="bi bi-alarm",
            url="lending:index",
            query_params="state=overdue",
        ),
        # LostRecord.objects is Record filtered to LOST with no is_active filter,
        # so the unfiltered-by-age record list under the same record_type matches
        # the count exactly.
        _build_tile(
            model_name="core.lostrecord",
            url="assets:record_index",
            request=request,
            base_params={"record_type": Record.LOST},
        ),
        # One count per problem level instead of a single value. It links to the
        # whole journal; the period only applies to the counts.
        _tile(
            label=ngettext("Journal, last %(days)d day", "Journal, last %(days)d days", JOURNAL_TILE_DAYS)
            % {"days": JOURNAL_TILE_DAYS},
            value=None,
            level_counts=JournalEntry.objects.problem_counts(tenants=request.tenants, days=JOURNAL_TILE_DAYS),
            icon="bi bi-journal-text",
            url="journal:index",
        ),
    ]
    inventory = Inventory.objects.filter(is_active=True).first()
    if inventory:
        progress = inventory.get_inventory_progress(tenants=request.tenants)
        attention_tiles.append(
            _tile(
                label=str(inventory),
                value=progress.done_percent,
                unit="%",
                progress=progress.done_percent,
                caption=_("%(done)s of %(total)s devices")
                % {"done": progress.inventorized_devices_count, "total": progress.all_devices_count},
                icon=get_icon_for_class("core.inventory"),
                url="inventory:inventorize-room-list",
            )
        )

    stock_specs = [
        ("core.device", "assets:device_index"),
        ("core.lentrecord", "lending:index"),
        ("core.room", "rooms:index"),
        ("core.devicetype", "assets:device_type_index"),
        ("core.licencerecord", "licenses:index"),
        ("smallstuff.assignedthing", "smallstuff:person_search"),
    ]
    stock_tiles = [_build_tile(model_name=name, url=url, request=request) for name, url in stock_specs]

    device_type_ranking, device_type_total = stats.device_type_ranking(tenants=request.tenants)

    context = {
        "attention_tiles": attention_tiles,
        "stock_tiles": stock_tiles,
        "record_fraction_html": stats.get_record_fraction_html(tenants=request.tenants),
        "device_type_ranking": device_type_ranking,
        "device_type_total": device_type_total,
        "record_timeline_html": stats.get_record_timeline_html(tenants=request.tenants),
        **search_context,
    }
    return TemplateResponse(request, "dashboard/index.html", context)
