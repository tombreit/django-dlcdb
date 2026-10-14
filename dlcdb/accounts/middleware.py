# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth import middleware
from django_htmx.http import HttpResponseClientRefresh


class LoginRequiredMiddleware(middleware.LoginRequiredMiddleware):
    """
    Every view requires a login unless it is marked ``login_not_required``.

    Django's middleware, but an HTMX request is answered with a client-side
    refresh instead of the redirect: the browser reloads the page, and that
    full request gets the login redirect, with ``next`` pointing at the page
    rather than at the fragment. A plain redirect would swap the login page
    into the fragment's container.
    """

    def handle_no_permission(self, request, view_func):
        if request.htmx:
            return HttpResponseClientRefresh()
        return super().handle_no_permission(request, view_func)
