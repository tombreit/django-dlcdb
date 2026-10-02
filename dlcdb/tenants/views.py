# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The tenant frontend: which groups see which tenant, plus the tenant pages."""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Count, ProtectedError, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core.utils.helpers import get_denormalized_user

from .forms import TenantForm
from .models import Tenant


def _tenant_queryset():
    """
    Tenants with their device count and the count of active users who see them.
    Both counts are distinct: the two joins multiply each other's rows. Ordered
    explicitly: Django ignores Meta.ordering in GROUP BY queries.
    """
    return Tenant.objects.annotate(
        device_count=Count("device", distinct=True),
        user_count=Count("groups__user", filter=Q(groups__user__is_active=True), distinct=True),
    ).order_by(Lower("name"))


@permission_required("tenants.view_tenant", raise_exception=True)
def index(request):
    """
    A group × tenant checkbox matrix: a row is what a group sees, a column who
    sees a tenant. Each click is saved at once by ``toggle``. Deliberately not
    scoped to ``request.tenants``: whoever configures tenants must also see the
    tenants they are not in.
    """
    tenants = list(_tenant_queryset())
    groups = Group.objects.annotate(member_count=Count("user", filter=Q(user__is_active=True))).order_by("name")
    pairs = set(Tenant.groups.through.objects.values_list("tenant_id", "group_id"))
    # One row per group with one (tenant, checked) cell per tenant, so the
    # template only loops.
    rows = [(group, [(tenant, (tenant.pk, group.pk) in pairs) for tenant in tenants]) for group in groups]

    return TemplateResponse(
        request,
        "tenants/index.html",
        {"tenants": tenants, "rows": rows, "can_change": request.user.has_perm("tenants.change_tenant")},
    )


@require_POST
@permission_required("tenants.change_tenant", raise_exception=True)
def toggle(request, pk, group_pk):
    """
    One checkbox of the matrix (htmx). The checkbox posts the desired state
    ("sees" only when ticked), so a repeated request cannot invert it. Returns
    the tenant's footer cell with the updated count of users who see it.
    """
    tenant = get_object_or_404(Tenant, pk=pk)
    group = get_object_or_404(Group, pk=group_pk)
    sees = "sees" in request.POST

    # Only a real change is written: no audit stamp or history entry for a no-op.
    if sees != tenant.groups.filter(pk=group.pk).exists():
        if sees:
            tenant.groups.add(group)
        else:
            tenant.groups.remove(group)
        tenant.user, tenant.username = get_denormalized_user(request.user)
        tenant.save()

    return TemplateResponse(request, "tenants/index.html#user-count", {"tenant": _tenant_queryset().get(pk=pk)})


@permission_required("tenants.add_tenant", raise_exception=True)
def add(request):
    form = TenantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        tenant = form.save(commit=False)
        tenant.user, tenant.username = get_denormalized_user(request.user)
        tenant.save()
        messages.success(
            request,
            _("Tenant “%(tenant)s” was created. Tick the groups that should see it.") % {"tenant": tenant},
        )
        return redirect("tenants:index")

    return TemplateResponse(
        request,
        "tenants/form.html",
        {"form": form, "title": _("Add tenant"), "submit_label": _("Create tenant")},
    )


@permission_required("tenants.view_tenant", raise_exception=True)
def detail(request, pk):
    """Read and edit one tenant; its groups are edited in the matrix only."""
    tenant = get_object_or_404(_tenant_queryset(), pk=pk)
    can_change = request.user.has_perm("tenants.change_tenant")
    index_url = reverse("tenants:index")

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied
        form = TenantForm(request.POST, instance=tenant)
        if form.is_valid():
            tenant = form.save(commit=False)
            tenant.user, tenant.username = get_denormalized_user(request.user)
            tenant.save()
            messages.success(request, _("Tenant “%(tenant)s” was updated.") % {"tenant": tenant})
            return redirect(index_url)
    else:
        form = TenantForm(instance=tenant)

    import_count = tenant.importerlist_set.count()
    return TemplateResponse(
        request,
        "tenants/detail.html",
        {
            "tenant": tenant,
            "import_count": import_count,
            "form": form,
            "can_change": can_change,
            "index_url": index_url,
            "form_action": reverse("tenants:detail", args=[tenant.pk]),
            # PROTECT refuses a tenant with devices or imports, so only offer
            # Delete without them.
            "delete_url": (
                reverse("tenants:delete", args=[tenant.pk])
                if request.user.has_perm("tenants.delete_tenant") and not tenant.device_count and not import_count
                else None
            ),
        },
    )


@permission_required("tenants.delete_tenant", raise_exception=True)
def delete(request, pk):
    """Confirm, then hard delete. PROTECT refuses a tenant that still has devices or imports."""
    tenant = get_object_or_404(_tenant_queryset(), pk=pk)

    if request.method == "POST":
        try:
            tenant.delete()
        except ProtectedError:
            messages.error(
                request,
                _("Tenant “%(tenant)s” still has devices or imports and cannot be deleted.") % {"tenant": tenant},
            )
            return redirect("tenants:detail", pk=tenant.pk)
        messages.success(request, _("Tenant “%(tenant)s” was deleted.") % {"tenant": tenant})
        return redirect("tenants:index")

    return TemplateResponse(request, "tenants/delete.html", {"tenant": tenant})
