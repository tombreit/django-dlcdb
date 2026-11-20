# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Groups in the frontend: what their members may do, which tenants' devices they
see, and who they are (PLANS/users-and-groups.md).
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse

from dlcdb.core.utils.htmx import htmx_permission_required
from dlcdb.theme.navigation import get_redirect_url

from .permissions import own_permission_names, own_permissions, permission_name


def is_ldap_mirrored(group):
    """LDAP sets the members of this group at each login (``AUTH_LDAP_MIRROR_GROUPS``)."""
    mirrored = getattr(settings, "AUTH_LDAP_MIRROR_GROUPS", None)
    return mirrored is True or group.name in (mirrored or ())


@htmx_permission_required("accounts.view_group")
def index(request):
    """Every group with its active members, tenants and how many of DLCDB's own permissions it has."""
    own = own_permission_names()
    groups = (
        Group.objects.annotate(member_count=Count("user", filter=Q(user__is_active=True), distinct=True))
        .prefetch_related("tenant_set", "permissions__content_type")
        .order_by("name")
    )
    rows = [
        {
            "group": group,
            "ldap": is_ldap_mirrored(group),
            "permission_count": sum(permission_name(p) in own for p in group.permissions.all()),
        }
        for group in groups
    ]
    return TemplateResponse(request, "accounts/groups/index.html", {"rows": rows})


@htmx_permission_required("accounts.view_group")
def detail(request, pk):
    """One group: its permissions among DLCDB's own, the others it holds, its tenants and active members."""
    active_members = get_user_model().objects.filter(is_active=True).order_by("email")
    group = get_object_or_404(
        Group.objects.prefetch_related(
            "permissions__content_type", "tenant_set", Prefetch("user_set", queryset=active_members)
        ),
        pk=pk,
    )
    own = own_permissions()
    granted = {permission_name(p) for p in group.permissions.all()}
    own_names = {permission_name(p.permission) for p in own}

    return TemplateResponse(
        request,
        "accounts/groups/detail.html",
        {
            "group": group,
            "ldap": is_ldap_mirrored(group),
            "permissions": own,
            "granted": {p.permission.pk for p in own if permission_name(p.permission) in granted},
            # Not DLCDB's own: no page of DLCDB checks them, only the Django admin may.
            "other_permissions": sorted(granted - own_names),
            "next_url": get_redirect_url(request) or reverse("accounts:groups"),
        },
    )
