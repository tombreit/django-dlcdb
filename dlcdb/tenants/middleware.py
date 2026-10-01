# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.deprecation import MiddlewareMixin

from .shortcuts import get_user_tenants


class CurrentTenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets the `tenants` attribute (a tuple of the tenants the
    user may see) on the request object.
    """

    def process_request(self, request):
        request.tenants = get_user_tenants(request.user)
