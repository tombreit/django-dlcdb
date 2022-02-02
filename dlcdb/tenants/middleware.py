from django.utils.deprecation import MiddlewareMixin

from .shortcuts import get_current_tenant


class CurrentTenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets `tenant` attribute to request object.
    """

    def process_request(self, request):
        request.tenant = get_current_tenant(request)
