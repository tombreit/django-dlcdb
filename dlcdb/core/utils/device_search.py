# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Shared device live-search ranking, used by the centralized device picker
(``dlcdb.theme``). Both the lending and the relocate pickers feed it a
tenant-scoped ``Device`` queryset, so the search/relevance logic lives here once
instead of being copied per app.
"""

from django.db.models import Case, IntegerField, Q, When


def search_devices(queryset, value):
    """
    Filter and relevance-rank a ``core.Device`` queryset by ``value``.

    - empty value -> no results (the picker starts blank);
    - ``"*"``      -> the whole queryset, ordered by ``edv_id``;
    - otherwise    -> substring match on edv_id/sap_id/manufacturer/series/serial,
      ranked so model-name matches (manufacturer/series) lead over identifier
      matches over serial-only hits, then alphabetically by ``edv_id`` within a
      tier. A short query like "X1" thus surfaces the actual "Thinkpad X1"
      laptops ahead of coincidental edv_id/serial substring hits.
    """
    value = (value or "").strip()
    if not value:
        return queryset.none()
    if value == "*":
        return queryset.order_by("edv_id")

    return (
        queryset.filter(
            Q(edv_id__icontains=value)
            | Q(sap_id__icontains=value)
            | Q(manufacturer__name__icontains=value)
            | Q(series__icontains=value)
            | Q(serial_number__icontains=value)
        )
        .annotate(
            _rank=Case(
                When(Q(manufacturer__name__icontains=value) | Q(series__icontains=value), then=0),
                When(Q(edv_id__icontains=value) | Q(sap_id__icontains=value), then=1),
                default=2,
                output_field=IntegerField(),
            )
        )
        .order_by("_rank", "edv_id")
    )
