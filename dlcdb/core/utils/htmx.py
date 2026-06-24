# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
HTMX-aware request guards shared by the frontend apps (assets, lending,
licenses). Kept here in ``core.utils`` so there is a single implementation to
fix instead of one byte-for-byte copy per app.
"""

import functools

from django.contrib import messages
from django.contrib.auth.models import Permission
from django.contrib.auth.views import redirect_to_login
from django_htmx.http import HttpResponseClientRefresh


def htmx_login_required(view_func):
    """
    Login guard for endpoints reached over HTMX. An unauthenticated request
    triggers a full client-side refresh (the browser reloads and the normal
    login redirect takes over) instead of letting HTMX swap the login page's
    HTML into a results container. Non-HTMX requests get the usual login
    redirect.
    """

    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if getattr(request, "htmx", False):
                return HttpResponseClientRefresh()
            return redirect_to_login(request.get_full_path())
        return view_func(request, *args, **kwargs)

    return wrapped_view


def htmx_permission_required(perm):
    """
    Permission guard that plays nicely with HTMX requests: on a missing
    permission it flashes a message and triggers a client-side refresh instead
    of rendering Django's plain 403 page.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                # codename is not unique across apps, so a bare get() can raise
                # MultipleObjectsReturned — first() is enough for a message.
                perm_obj = Permission.objects.filter(codename=perm.split(".")[-1]).first()
                messages.error(request, f"Permission denied. You need the permission: {perm_obj or perm}")
                return HttpResponseClientRefresh()
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
