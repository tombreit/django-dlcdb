# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Where a page returns to: the ``?next=<local URL>`` parameter.

A link that opens a page passes the page it is on as ``next``. A list passes
itself, with its search, filters, sort and page, so Back, Cancel and Save on the
detail page return to exactly that list; the inventory search passes itself to
a device's state change. In a template:
``?next={{ request.get_full_path|urlencode }}``.

An add page can also hand the new object back: with ``?next_field=<name>``,
saving returns to ``next`` with ``<name>=<new pk>`` set, for the form there to
preselect (``get_redirect_url_after_add``).

Name and meaning are Django's own: ``next`` is what the login and
``set_language`` read (``django.contrib.auth.REDIRECT_FIELD_NAME``), and
``get_redirect_url`` is the function form of Django's
``RedirectURLMixin.get_redirect_url``.

Pure functions, no template tag — the same convention as ``theme.pagination``.
"""

from urllib.parse import urlsplit, urlunsplit

from django.http import HttpRequest, QueryDict
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def get_redirect_url(request: HttpRequest) -> str:
    """
    Return the request's ``next`` URL if it is safe, otherwise ``""``. As in
    Django, POST wins over GET and only URLs on this host are safe; callers
    write ``get_redirect_url(request) or <default URL>``.

    Unlike Django, ``next`` must also be a path: the lists used to send their
    bare query string as ``next``, which Django's check accepts as a relative
    URL. An old link with ``next=search%3D…`` falls back to the default instead
    of leading to ``<detail page>/search=…``.
    """
    redirect_to = request.POST.get("next", request.GET.get("next", ""))
    url_is_safe = redirect_to.startswith("/") and url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    return redirect_to if url_is_safe else ""


def get_redirect_url_after_add(request: HttpRequest, pk) -> str:
    """
    Return ``get_redirect_url(request)`` with the new object's pk set as
    ``<next_field>=<pk>``, replacing an earlier value of that parameter.

    ``next_field`` is the HTML name of the select whose + button opened the add
    page. Without one, or with one that is not a plain field name, this is just
    ``get_redirect_url(request)``; without a safe ``next`` it is ``""`` too.
    """
    redirect_to = get_redirect_url(request)
    field_name = request.POST.get("next_field", request.GET.get("next_field", ""))
    if not redirect_to or not field_name.isidentifier():
        return redirect_to
    return _with_parameter(redirect_to, field_name, str(pk))


def with_next(url: str, redirect_to: str | None) -> str:
    """
    Return ``url`` with ``next=<redirect_to>`` added to its query string, or
    unchanged without ``redirect_to``.
    """
    return _with_parameter(url, "next", redirect_to) if redirect_to else url


def _with_parameter(url: str, name: str, value: str) -> str:
    """
    Return ``url`` with ``name=value`` set in its query string. Encoded like
    Django's ``redirect_to_login``, which keeps the slashes readable.
    """
    parts = urlsplit(url)
    query = QueryDict(parts.query, mutable=True)
    query[name] = value
    return urlunsplit(parts._replace(query=query.urlencode(safe="/")))


def detail_urls(request: HttpRequest, index_route: str, detail_route: str, pk) -> tuple[str, str]:
    """
    Return ``(next_url, form_action)`` for a detail page: where Back, Cancel and
    Save lead (the safe ``next``, otherwise the index), and the form's action,
    which carries ``next`` through the POST.
    """
    redirect_to = get_redirect_url(request)
    form_action = with_next(reverse(detail_route, args=[pk]), redirect_to)
    return redirect_to or reverse(index_route), form_action
