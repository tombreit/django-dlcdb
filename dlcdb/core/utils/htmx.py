# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
HTMX-aware request guards shared by the frontend apps (assets, lending,
licenses). Kept here in ``core.utils`` so there is a single implementation to
fix instead of one byte-for-byte copy per app. The login itself is checked for
every view by ``dlcdb.accounts.middleware.LoginRequiredMiddleware``.
"""

import functools

from django.contrib import messages
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.utils.translation import ngettext
from django_htmx.http import HttpResponseClientRefresh


def missing_permission_message(*perms):
    """
    Name the permissions ("app_label.codename") a request lacks, as the group
    admin lists them, so the user can ask for exactly that. Several permissions
    are alternatives, as in ``htmx_permission_required``.
    """
    names = []
    for perm in perms:
        app_label, codename = perm.split(".")
        # codename is unique per model, not per app: first() is enough for a name.
        permission = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
        names.append(str(permission or perm))
    return ngettext(
        "Permission denied. You need the permission: %(permissions)s",
        "Permission denied. You need one of these permissions: %(permissions)s",
        len(names),
    ) % {"permissions": ", ".join(names)}


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
                message = missing_permission_message(*perms)
                if getattr(request, "htmx", False):
                    messages.error(request, message)
                    return HttpResponseClientRefresh()
                raise PermissionDenied(message)
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
