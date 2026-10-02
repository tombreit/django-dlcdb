# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tenant scoping: the single place that turns a user's groups into the tenants
they may see, and the helpers that apply this to querysets and form fields.
The middleware stores the result as ``request.tenants``.
"""

from .models import Tenant


def get_user_tenants(user):
    """
    Tenants whose groups the user belongs to; several tenants mean their union.
    No exception for superusers: to see every tenant, a group is attached to
    every tenant.
    """
    if not user.is_authenticated:
        return ()
    return tuple(Tenant.objects.filter(groups__user=user).distinct())


def tenant_scoped_queryset(queryset, request, *, tenant_field="tenant"):
    """
    Restrict ``queryset`` to the request's tenants. ``tenant_field`` is the
    lookup path to the tenant: ``"tenant"`` for devices, ``"device__tenant"``
    for records. Objects without a tenant are never included.
    """
    return queryset.filter(**{f"{tenant_field}__in": request.tenants})


def limit_tenant_field(field, tenants):
    """
    Offer only the given tenants; with exactly one, preselect it as the only
    option. The field stays required: a foreign tenant fails validation, and
    without tenants the form cannot be valid.
    """
    field.queryset = Tenant.objects.filter(pk__in=[tenant.pk for tenant in tenants])
    if len(tenants) == 1:
        field.initial = tenants[0]
        field.empty_label = None
