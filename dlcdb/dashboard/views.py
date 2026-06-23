# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse

from dlcdb.core.models import Inventory, Record
from dlcdb.core.utils.helpers import get_icon_for_class

from . import stats


# Map each dashboard model to the field path used to scope its queryset to a
# tenant. Mirrors core.views.dashboard_views.DashboardView.
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

    qs = ModelClass.objects.filter(**{filter_field: tenant})
    if model_name in TENANT_DISTINCT:
        qs = qs.distinct()
    return qs


def _build_tile(*, model_name, url, tenant):
    """Build the context dict for a single dashboard tile."""
    ModelClass = apps.get_model(model_name)
    qs = _get_tenant_queryset(model_name, ModelClass, tenant)

    raw_count = qs.count()
    human_name = ModelClass._meta.verbose_name_plural if raw_count >= 2 else ModelClass._meta.verbose_name

    note_count = 0
    if hasattr(ModelClass, "note"):
        note_count = qs.exclude(note__exact="").count()

    count = raw_count
    if model_name == "core.lentrecord":
        lent_count = qs.filter(record_type=Record.LENT).count()
        count = f"{lent_count} / {raw_count}"
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
    New-frontend dashboard: model tiles (counts + note badges) and Plotly stats,
    rebuilt on the theme app. Mirrors core.views.dashboard_views.DashboardView.
    """
    tenant = request.tenant

    tile_specs = [
        ("core.device", "admin:core_device_changelist"),
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

    context = {
        "tiles": tiles,
        "record_fraction_html": stats.get_record_fraction_html(tenant=tenant),
        "device_type_html": stats.get_device_type_html(tenant=tenant),
        "record_timeline_html": stats.get_record_timeline_html(tenant=tenant),
    }
    return TemplateResponse(request, "dashboard/index.html", context)
