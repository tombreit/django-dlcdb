# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tenant scoping shared by the frontend apps. Single implementation of the
visibility policy used by ``dlcdb.tenants.admin.TenantScopedAdmin`` so it does
not drift between per-app copies.
"""


def tenant_scoped_queryset(queryset, request, *, tenant_field="tenant"):
    """
    Scope ``queryset`` to the request's tenant, mirroring
    ``dlcdb.tenants.admin.TenantScopedAdmin``: with a tenant set on the request
    everyone (including superusers) is scoped to it; without a tenant only
    superusers see everything, others see nothing.

    ``tenant_field`` is the lookup path to the tenant from the queryset's model
    — ``"tenant"`` for devices, ``"device__tenant"`` for records.
    """
    tenant = getattr(request, "tenant", None)
    if tenant:
        return queryset.filter(**{tenant_field: tenant})
    if request.user.is_superuser:
        return queryset
    return queryset.none()
