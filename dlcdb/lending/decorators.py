# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import messages
from django.contrib.auth.models import Permission
from django_htmx.http import HttpResponseClientRefresh


def htmx_permission_required(perm):
    """
    Permission guard that plays nicely with HTMX requests: on a missing
    permission it flashes a message and triggers a client-side refresh instead
    of rendering Django's plain 403 page. Mirrors
    ``dlcdb.licenses.decorators.htmx_permission_required``.
    """

    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                try:
                    perm_obj = Permission.objects.get(codename=perm.split(".")[-1])
                    messages.error(
                        request,
                        f"Permission denied. You need the permission: {perm_obj}",
                    )
                except Permission.DoesNotExist:
                    messages.error(request, f"Permission denied. You need the permission: {perm}")
                return HttpResponseClientRefresh()
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
