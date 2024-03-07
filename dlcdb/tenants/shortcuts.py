# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import messages


def get_current_tenant(request):
    """
    Get current ``Tenant`` object based on request.user.groups.
    """

    from .models import Tenant

    tenant = request_user_groups = None

    if request.user.is_authenticated and not request.user.is_superuser:
        try:
            request_user_groups = request.user.groups.all()
            _tenant = (
                Tenant.objects.filter(groups__in=request_user_groups)
                # Multiple tenent matches ares possible, so we could not use .get()
                # https://docs.djangoproject.com/en/3.2/ref/models/querysets/#get
                .distinct()
            )
            _tenant_count = _tenant.count()
        except Exception as e:
            messages.error(f"Something went wrong getting a tenant from a request! Error was: {e}")
            pass

        if _tenant_count >= 2:
            messages.add_message(
                request,
                messages.ERROR,
                f"Expected one matched tenant, but got mulitple: '{_tenant}'. Tenant-scoped querysets will not return any objects!",
            )
        elif _tenant_count == 0:
            messages.add_message(
                request,
                messages.ERROR,
                f"Could not find a tenant for user '{request.user}' with groups '{request_user_groups}'. Tenant-scoped querysets will not return any objects!",
            )
        elif _tenant_count == 1:
            tenant = _tenant.get()
        else:
            messages.add_message(
                request,
                messages.ERROR,
                f"Something went wrong getting a tenant for user '{request.user}' with groups '{request_user_groups}'. Tenant-scoped querysets will not return any objects!",
            )

    return tenant
