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
from django.core.exceptions import PermissionDenied
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


def _missing_permission_message(perms):
    """Name the permissions a request lacks, in the wording end users see."""
    # codename is not unique across apps, so a bare get() can raise
    # MultipleObjectsReturned — first() is enough for a message.
    names = []
    for perm in perms:
        perm_obj = Permission.objects.filter(codename=perm.split(".")[-1]).first()
        names.append(str(perm_obj or perm))
    return f"Permission denied. You need the permission: {' or '.join(names)}"


def htmx_permission_required(*perms):
    """
    Permission guard that plays nicely with HTMX requests: on a missing
    permission it flashes a message and triggers a client-side refresh instead
    of swapping an error page into a fragment container. A plain navigation gets
    the ordinary 403 instead -- answering it with the client-refresh response
    would render as an empty 200 body, i.e. a blank page whose reason only
    surfaces on whatever page the user happens to open next.

    Several permissions mean *any one of them* suffices, for views that front
    more than one lifecycle move (the room picker serves locate, relocate and
    find). Django's own ``permission_required`` requires all of a list, which is
    the opposite of what those views need.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not any(request.user.has_perm(perm) for perm in perms):
                message = _missing_permission_message(perms)
                if getattr(request, "htmx", False):
                    messages.error(request, message)
                    return HttpResponseClientRefresh()
                raise PermissionDenied(message)
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
