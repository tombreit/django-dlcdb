# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import BooleanField, Case, CharField, Count, IntegerField, Q, Value, When
from django.template.response import TemplateResponse

from dlcdb.core.models import LentRecord, Record

from .filters import LentRecordFilter, STATE_OVERDUE, STATE_LENT, STATE_AVAILABLE
from .models import LendingConfiguration


def _tenant_scoped(queryset, request):
    """
    Scope a record queryset to the current tenant, mirroring
    dlcdb.tenants.admin.TenantScopedAdmin: if a tenant is set on the request,
    everyone (including superusers) is scoped to it; without a tenant only
    superusers see all records, others see nothing. Records carry no tenant
    field of their own, so we filter via the related device.
    """
    tenant = getattr(request, "tenant", None)
    if tenant:
        return queryset.filter(device__tenant=tenant)
    if request.user.is_superuser:
        return queryset
    return queryset.none()


def _annotate_lent_state(queryset):
    """
    Annotate each record with a display state, a matching Bootstrap contextual
    color and a sort weight (most urgent first). Whether overdue lendings are
    highlighted is controlled by LendingConfiguration.admin_mark_overdue.
    """
    today = datetime.date.today()
    mark_overdue = LendingConfiguration.load().admin_mark_overdue
    overdue = Q(lent_desired_end_date__lte=today) & Q(lent_end_date__isnull=True)

    state_whens, color_whens, sort_whens = [], [], []

    if mark_overdue:
        state_whens.append(When(overdue, then=Value(STATE_OVERDUE)))
        color_whens.append(When(overdue, then=Value("danger")))
        # Available first, then overdue at the top of the lent group, then lent.
        sort_whens.append(When(overdue, then=Value(2)))

    state_whens += [
        When(record_type=Record.LENT, then=Value(STATE_LENT)),
        When(record_type=Record.INROOM, then=Value(STATE_AVAILABLE)),
    ]
    color_whens += [
        When(record_type=Record.LENT, then=Value("warning")),
        When(record_type=Record.INROOM, then=Value("success")),
    ]
    sort_whens += [
        When(record_type=Record.INROOM, then=Value(1)),
        When(record_type=Record.LENT, then=Value(3)),
    ]

    return queryset.annotate(
        lent_state=Case(*state_whens, default=Value("unknown"), output_field=CharField()),
        lent_state_color=Case(*color_whens, default=Value("secondary"), output_field=CharField()),
        lent_state_sort=Case(*sort_whens, default=Value(9), output_field=IntegerField()),
        # Always computed, independent of admin_mark_overdue, so the due-date
        # column can flag genuinely overdue lendings.
        is_overdue=Case(When(overdue, then=Value(True)), default=Value(False), output_field=BooleanField()),
    ).order_by("lent_state_sort", "device__edv_id")


@login_required
def index(request):
    """
    Overview of lendable devices: what is currently lent to whom and what is
    available, with live HTMX search/filtering and bookmarkable URLs.
    """
    template = "lending/index.html#lent-list" if request.htmx else "lending/index.html"

    base_qs = _annotate_lent_state(
        _tenant_scoped(
            LentRecord.objects.select_related("device__manufacturer", "person", "room"),
            request,
        )
    )

    lent_record_filter = LentRecordFilter(request.GET, queryset=base_qs, request=request)

    counts = lent_record_filter.qs.aggregate(
        total=Count("pk"),
        available=Count("pk", filter=Q(record_type=Record.INROOM)),
        lent=Count("pk", filter=Q(record_type=Record.LENT)),
    )

    context = {
        "filter": lent_record_filter,
        "lent_filtered_count": counts["total"],
        "lent_total_count": base_qs.count(),
        "lent_available_count": counts["available"],
        "lent_lent_count": counts["lent"],
    }

    return TemplateResponse(request, template, context)
