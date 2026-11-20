# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Groups in the frontend: what their members may do, which tenants' devices they
see, and who they are. A new group has the same page, without a group.
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
from dlcdb.theme.forms import disable_fields
from dlcdb.theme.navigation import get_redirect_url

from .forms import GroupForm, may_still_change_groups
from .group_profiles import GROUP_PROFILES
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
    """One group: its permissions among DLCDB's own, its members and its tenants. Saving needs ``change_group``."""
    group = get_object_or_404(Group, pk=pk)
    can_change = request.user.has_perm("accounts.change_group")
    if request.method == "POST" and not can_change:
        raise PermissionDenied(missing_permission_message("accounts.change_group"))
    return _group_page(request, group, can_change=can_change)


@htmx_permission_required("accounts.add_group")
def add(request):
    """A new group: the group page without a group."""
    return _group_page(request, Group(), can_change=True)


def _group_page(request, group, *, can_change):
    """The group page of ``group``, saved or new: the form, saved on POST. The views check the permissions."""
    new = group.pk is None
    next_url = get_redirect_url(request) or reverse("accounts:groups")
    own = own_permissions()
    form = GroupForm(request.POST or None, instance=group, own=own, editor=request.user)
    if form.is_valid():
        form.save()
        _journal(form, event="created" if new else "changed", user=request.user)
        message = _("Group “{group}” was created.") if new else _("Group “{group}” was updated.")
        messages.success(request, linked_message(message, group=group))
        return redirect(next_url)
    if not can_change:
        disable_fields(form)

    tenants_field = form.fields.get("tenants")
    return TemplateResponse(
        request,
        "accounts/groups/detail.html",
        {
            "group": group,
            "form": form,
            "can_change": can_change,
            "submit_label": _("Create group") if new else None,
            "ldap": not new and is_ldap_mirrored(group),
            "permissions": own,
            "checked": {p.pk for p in form.checked("permissions")},
            "other_permissions": [] if new else _other_permissions(group, own),
            # With the permission to tick them: every tenant; otherwise the group's, read-only.
            "all_tenants": tenants_field.queryset if tenants_field else None,
            "checked_tenants": {tenant.pk for tenant in form.checked("tenants")} if tenants_field else set(),
            "group_tenants": [] if new else group.tenant_set.order_by("name"),
            # Each button ticks its profile's permissions (accounts/js/group-profiles.js).
            "profiles": [
                (profile, list(profile.permissions().values_list("pk", flat=True))) for profile in GROUP_PROFILES
            ],
            "next_url": next_url,
            "form_action": request.get_full_path(),
            "delete_url": (
                reverse("accounts:group_delete", args=[group.pk])
                if not new and request.user.has_perm("accounts.delete_group")
                else None
            ),
        },
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
            tenant.set_visible_to(group, False, user=request.user)
        group.delete()
        messages.success(request, _("Group “%(group)s” was deleted.") % {"group": group.name})
        return redirect("accounts:groups")

    return TemplateResponse(
        request, "accounts/groups/delete.html", {"group": group, "members": members, "ldap": is_ldap_mirrored(group)}
    )


def _other_permissions(group, own):
    """The group's permissions that aren't DLCDB's own: no page of DLCDB checks them, only the Django admin may."""
    own_pks = {p.permission.pk for p in own}
    return sorted(permission_name(p) for p in group.permissions.select_related("content_type") if p.pk not in own_pks)


def _journal(form, *, event, user):
    """
    One journal entry naming what changed, ``event`` "created" or "changed"; a
    new group's form starts empty. The text is in English, like every journal entry.
    """
    group = form.instance
    with translation.override(None):
        labels = {p.permission: str(p) for p in form.own}
        changes = []
        if event == "changed" and "name" in form.changed_data:
            changes.append(f"Renamed from {form.initial['name']}")
        changes += _added_and_removed(
            "Permissions", form.initial["permissions"], form.cleaned_data["permissions"], labels.get
        )
        for name in ("members", "tenants"):
            if name in form.fields and not form.fields[name].disabled:
                changes += _added_and_removed(name.capitalize(), form.initial[name], form.cleaned_data[name], str)
    if changes or event == "created":
        JournalEntry.objects.log(
            source="accounts.groups",
            event=event,
            summary=f"Group {group} {event}",
            body="\n".join(changes),
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
