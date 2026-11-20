# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Groups in the frontend: what their members may do, which tenants' devices they
see, and who they are (PLANS/users-and-groups.md).
"""

from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from dlcdb.core.utils.htmx import htmx_permission_required, missing_permission_message
from dlcdb.core.utils.links import linked_message
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.models import Tenant
from dlcdb.theme.forms import disable_fields
from dlcdb.theme.navigation import get_redirect_url

from .forms import GroupForm, NewGroupForm, may_still_change_groups
from .group_profiles import BY_KEY, GROUP_PROFILES
from .models import is_ldap_mirrored
from .permissions import own_permission_names, own_permissions, permission_name


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
    """
    One group: its permissions among DLCDB's own, its members and its tenants.
    Saving needs ``accounts.change_group``; the tenants card saves each tick
    through the tenant matrix's own view.

    A group profile's button saves the form with the profile's permissions
    added, and returns here to show them.
    """
    group = get_object_or_404(Group, pk=pk)
    can_change = request.user.has_perm("accounts.change_group")
    next_url = get_redirect_url(request) or reverse("accounts:groups")
    own = own_permissions()

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied(missing_permission_message("accounts.change_group"))
        profile = BY_KEY.get(request.POST.get("add_profile"))
        data = _with_profile_ticked(request.POST, profile) if profile else request.POST
        form = GroupForm(data, instance=group, own=own, editor=request.user)
        if form.is_valid():
            form.save()
            _journal_changes(form, user=request.user)
            if profile:
                messages.success(
                    request,
                    _("The permissions of the group profile “%(profile)s” were added.") % {"profile": profile.label},
                )
                return redirect(request.get_full_path())
            messages.success(request, linked_message(_("Group “{group}” was updated."), group=group))
            return redirect(next_url)
    else:
        form = GroupForm(instance=group, own=own, editor=request.user)
        if not can_change:
            disable_fields(form)

    own_pks = {p.permission.pk for p in own}
    return TemplateResponse(
        request,
        "accounts/groups/detail.html",
        {
            "group": group,
            "form": form,
            "can_change": can_change,
            "ldap": is_ldap_mirrored(group),
            "permissions": own,
            "checked": {p.pk for p in form.checked_permissions()},
            # Not DLCDB's own: no page of DLCDB checks them, only the Django admin may.
            "other_permissions": sorted(
                permission_name(p) for p in group.permissions.select_related("content_type") if p.pk not in own_pks
            ),
            "group_tenants": group.tenant_set.order_by("name"),
            # With the permission to tick them: every tenant, ticked where the group sees it.
            "all_tenants": Tenant.objects.order_by("name") if request.user.has_perm("tenants.change_tenant") else None,
            "profiles": GROUP_PROFILES,
            "next_url": next_url,
            "form_action": request.get_full_path(),
            "delete_url": (
                reverse("accounts:group_delete", args=[group.pk])
                if request.user.has_perm("accounts.delete_group")
                else None
            ),
        },
    )


@htmx_permission_required("accounts.add_group")
def add(request):
    """A new group from a group profile, with a tenant and members; then its page, to adjust it."""
    form = NewGroupForm(request.POST or None, editor=request.user)
    if request.method == "POST" and form.is_valid():
        group = form.save()
        _journal_new(form, user=request.user)
        messages.success(request, _("Group “%(group)s” was created.") % {"group": group})
        return redirect("accounts:group_detail", pk=group.pk)

    return TemplateResponse(
        request,
        "accounts/groups/add.html",
        {"form": form, "profiles": GROUP_PROFILES, "next_url": get_redirect_url(request) or reverse("accounts:groups")},
    )


@htmx_permission_required("accounts.delete_group")
def delete(request, pk):
    """
    Confirm, then delete. Its members lose what the group gave them. Not one's
    only way to change groups: no locking oneself out.
    """
    group = get_object_or_404(Group, pk=pk)
    members = group.user_set.filter(is_active=True).order_by("email")

    if request.method == "POST":
        if request.user.has_perm("accounts.change_group") and not may_still_change_groups(request.user, without=group):
            messages.error(request, _("You cannot delete this group: it is your only way to change groups."))
            return redirect("accounts:group_detail", pk=group.pk)
        _journal_deleted(group, members=members, user=request.user)
        # Removed like an untick in the tenant matrix: stamped, into the tenant's history.
        for tenant in group.tenant_set.all():
            tenant.groups.remove(group)
            tenant.stamp_user(request.user)
            tenant.save()
        group.delete()
        messages.success(request, _("Group “%(group)s” was deleted.") % {"group": group.name})
        return redirect("accounts:groups")

    return TemplateResponse(
        request, "accounts/groups/delete.html", {"group": group, "members": members, "ldap": is_ldap_mirrored(group)}
    )


def _with_profile_ticked(data, profile):
    """The submitted group form with the profile's permissions ticked as well."""
    data = data.copy()
    profile_pks = profile.permissions().values_list("pk", flat=True)
    data.setlist("permissions", [*data.getlist("permissions"), *map(str, profile_pks)])
    return data


def _journal_changes(form, *, user):
    """One journal entry naming what changed; the text is in English, like every journal entry."""
    group = form.instance
    with translation.override(None):
        labels = {p.permission: str(p) for p in form.own}
        changes = []
        if "name" in form.changed_data:
            changes.append(f"Renamed from {form.initial['name']}")
        changes += _added_and_removed(
            "Permissions", form.initial["permissions"], form.cleaned_data["permissions"], labels.get
        )
        if "members" in form.fields and not form.fields["members"].disabled:
            changes += _added_and_removed("Members", form.initial["members"], form.cleaned_data["members"], str)
    if changes:
        JournalEntry.objects.log(
            source="accounts.groups",
            event="changed",
            summary=f"Group {group} changed",
            body="\n".join(changes),
            user=user,
            subject=group,
        )


def _journal_new(form, *, user):
    group, data = form.instance, form.cleaned_data
    with translation.override(None):
        details = [
            f"Group profile: {BY_KEY[data['profile']].label}" if data["profile"] else "",
            f"Tenant: {data['tenant']}" if data.get("tenant") else "",
            f"Members: {', '.join(map(str, data['members']))}" if data.get("members") else "",
        ]
    JournalEntry.objects.log(
        source="accounts.groups",
        event="created",
        summary=f"Group {group} created",
        body="\n".join(filter(None, details)),
        user=user,
        subject=group,
    )


def _journal_deleted(group, *, members, user):
    tenants = ", ".join(tenant.name for tenant in group.tenant_set.order_by("name"))
    details = [f"Members: {', '.join(map(str, members))}" if members else "", f"Tenants: {tenants}" if tenants else ""]
    # No subject: the group is gone; the summary keeps its name.
    JournalEntry.objects.log(
        source="accounts.groups",
        event="deleted",
        summary=f"Group {group} deleted",
        body="\n".join(filter(None, details)),
        user=user,
    )


def _added_and_removed(what, before, after, label):
    before, after = set(before), set(after)
    lines = []
    if added := after - before:
        lines.append(f"{what} added: {', '.join(sorted(map(label, added)))}")
    if removed := before - after:
        lines.append(f"{what} removed: {', '.join(sorted(map(label, removed)))}")
    return lines
