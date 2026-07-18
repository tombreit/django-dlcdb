# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import date

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models import Inventory, LentRecord, Record
from dlcdb.core.utils.helpers import get_icon_for_class

from . import stats


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


def _get_tenant_queryset(model_name, ModelClass, tenant):
    if tenant is None:
        return ModelClass.objects.all()

    filter_field = TENANT_FILTERS.get(model_name)
    if filter_field is None:
        return ModelClass.objects.all()

    # Distinctness is applied in _build_tile via Count(distinct=...), not here,
    # so it is expressed once at the aggregation.
    return ModelClass.objects.filter(**{filter_field: tenant})


def _build_tile(*, model_name, url, tenant):
    """Build the context dict for a single dashboard tile."""
    ModelClass = apps.get_model(model_name)
    qs = _get_tenant_queryset(model_name, ModelClass, tenant)

    # Collapse the per-tile counts (total, note badge, lent) into a single
    # aggregate query instead of 2-3 separate .count() scans over the same rows.
    distinct = model_name in TENANT_DISTINCT and tenant is not None
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

    return {
        "label": human_name,
        "count": count,
        "note_count": note_count,
        "show_badge": bool(note_count) and model_name not in NO_BADGE_MODELS,
        "icon": get_icon_for_class(model_name),
        "url": url,
        "query_params": "has_note=has_note" if note_count else "",
    }


@login_required
def index(request):
    """
    Dashboard on the theme frontend: model tiles (counts + note badges) and
    Plotly stats, scoped to the current tenant.
    """
    tenant = request.tenant

    tile_specs = [
        ("core.device", "assets:device_index"),
        ("core.lentrecord", "lending:index"),
        ("core.room", "admin:core_room_changelist"),
        ("core.devicetype", "admin:core_devicetype_changelist"),
        ("core.licencerecord", "licenses:index"),
        ("smallstuff.assignedthing", "smallstuff:person_search"),
        ("core.lostrecord", "admin:core_lostrecord_changelist"),
    ]
    if Inventory.objects.filter(is_active=True).exists():
        tile_specs.append(("core.inventory", "inventory:inventorize-room-list"))

    tiles = [_build_tile(model_name=name, url=url, tenant=tenant) for name, url in tile_specs]

    # Overdue tile: same predicate as the lending list's "state=overdue" filter
    # (lending/filters.py), so the count always matches the linked list.
    overdue_qs = LentRecord.objects.filter(
        lent_desired_end_date__lte=date.today(),
        lent_end_date__isnull=True,
    )
    if tenant:
        overdue_qs = overdue_qs.filter(device__tenant=tenant)
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

    context = {
        "tiles": tiles,
        "record_fraction_html": stats.get_record_fraction_html(tenant=tenant),
        "device_type_html": stats.get_device_type_html(tenant=tenant),
        "record_timeline_html": stats.get_record_timeline_html(tenant=tenant),
    }
    return TemplateResponse(request, "dashboard/index.html", context)
