# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Export-link helper for filtered list pages.

Sits beside the other pure list-page helpers (``theme.filterbar``,
``theme.pagination``): a view calls it and puts the result in its context, so no
custom template tag is involved.
"""

from django.http import QueryDict
from django.urls import reverse


def export_href(request, url_name, *, drop=("page", "show_all")):
    """The export URL carrying this list's current search, filters and ordering.

    ``drop`` names parameters that are pagination state and therefore meaningless
    for an export that always covers every matching row. Empty values are dropped
    too: every filter reads them as "not filtering", and the filterbar submits its
    whole form, so without this the href collects a dozen ``&state=&person=``
    pairs on every HTMX swap. What is left is a URL worth copying and sharing.

    Built here rather than with the builtin ``{% querystring %}`` tag, which
    rebuilds ``request.path`` -- the list endpoint, not the export one.
    """
    query = QueryDict(mutable=True)
    for param, values in request.GET.lists():
        if param in drop:
            continue
        query.setlist(param, [value for value in values if value])

    encoded = query.urlencode()
    url = reverse(url_name)
    return f"{url}?{encoded}" if encoded else url
