# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Reusable pagination for the custom frontend.

A single ``paginate`` helper plus ``theme/includes/_pagination.html`` give any
list view a numbered, HTMX-aware pager. Pure function, no template tag — the
same convention the filterbar follows.
"""

from django.core.paginator import Page, Paginator
from django.http import HttpRequest
from django.db.models import QuerySet


def paginate(
    request: HttpRequest,
    queryset: QuerySet,
    per_page: int = 25,
    *,
    on_each_side: int = 1,
    on_ends: int = 1,
) -> Page:
    """
    Return the requested ``Page`` of ``queryset`` (``?page=`` from the request).

    ``get_page`` clamps out-of-range/garbage page numbers to a valid page, so the
    caller never has to guard the input. A windowed page range (with ``…``
    sentinels) is precomputed onto the page as ``elided_page_range`` because a
    template cannot call ``get_elided_page_range()`` with arguments itself; the
    pager template just iterates it.
    """
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.GET.get("page"))
    page.elided_page_range = list(
        paginator.get_elided_page_range(page.number, on_each_side=on_each_side, on_ends=on_ends)
    )
    return page
