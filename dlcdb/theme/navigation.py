# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
List-to-detail navigation for the custom frontend.

The index pages thread their active search/filter/sort state to a detail page as
``?next=<querystring>``. The detail page has to hand that state back in three
places — Back, Cancel and the form's own action — so that saving returns to the
exact filtered list instead of a bare index.

``?back=<URL>`` is the other direction: a screen that sends users to a shared
form, e.g. the inventory search to a device's state change, passes its own URL
so the form returns there instead of to its default page.

Pure functions, no template tag — the same convention as ``theme.pagination``.
"""

from django.http import HttpRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode


def index_url(request: HttpRequest, route: str) -> str:
    """
    Return the index URL for ``route``, carrying ``?next=`` back as the actual
    query string. ``next`` already *is* a querystring, so it is appended raw
    rather than re-encoded as a parameter.
    """
    url = reverse(route)
    next_query = request.GET.get("next", "")
    return f"{url}?{next_query}" if next_query else url


def detail_urls(request: HttpRequest, index_route: str, detail_route: str, pk) -> tuple[str, str]:
    """
    Return ``(index_url, form_action)`` for a detail page.

    Unlike the index link, ``form_action`` keeps ``next`` as a *parameter*: the
    POST lands back on the detail view, which reads it from GET again to rebuild
    both URLs after the save.
    """
    form_action = reverse(detail_route, args=[pk])
    next_query = request.GET.get("next", "")
    if next_query:
        form_action += "?" + urlencode({"next": next_query})
    return index_url(request, index_route), form_action


def back_url(request: HttpRequest, default: str) -> str:
    """Return the request's ``?back=`` URL, or ``default`` if it has none or it leads off this site."""
    back = request.GET.get("back", "")
    if back and url_has_allowed_host_and_scheme(
        back, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return back
    return default


def with_back(url: str, back: str | None) -> str:
    """Return ``url`` with ``?back=<back>`` for ``back_url``, or unchanged without ``back``."""
    return f"{url}?{urlencode({'back': back})}" if back else url
