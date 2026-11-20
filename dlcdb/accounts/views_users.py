# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Users in the frontend: who has an account, their groups, what they may do and
which tenants' devices they see; deactivating them (PLANS/users-and-groups.md).
The Staff and Superuser flags stay with the Django admin, LDAP and createsuperuser.
"""

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core.utils.htmx import htmx_permission_required
from dlcdb.journal.models import JournalEntry
from dlcdb.tenants.shortcuts import get_user_tenants
from dlcdb.theme.filterbar import bind_filterset, build_filterbar
from dlcdb.theme.navigation import get_redirect_url
from dlcdb.theme.pagination import paginate

from .filters import UserFilter
from .models import CustomUser, is_ldap_mirrored
from .permissions import own_permissions, permission_name

USERS_PER_PAGE = 50


@htmx_permission_required("accounts.view_customuser")
def index(request):
    """Every account, deactivated ones too, with its groups."""
    template = "accounts/users/index.html#user-list" if request.htmx else "accounts/users/index.html"
    base_queryset = CustomUser.objects.prefetch_related("groups")
    user_filter = bind_filterset(UserFilter, request, base_queryset, default_ordering="email")
    page_obj = paginate(request, user_filter.qs, USERS_PER_PAGE)

    context = {
        "filter": user_filter,
        "page_obj": page_obj,
        "filterbar": build_filterbar(
            user_filter, request, target="#user-list", search_placeholder=_("Search email, name...")
        ),
        "current_ordering": user_filter.data["ordering"],
        "filtered_count": page_obj.paginator.count,
        "total_count": base_queryset.count(),
    }
    return TemplateResponse(request, template, context)


@htmx_permission_required("accounts.view_customuser")
def detail(request, pk):
    """One account: its groups, what it may do through them, the tenants it sees."""
    user = get_object_or_404(CustomUser, pk=pk)
    # A superuser may do everything, a deactivated user nothing: the page says so instead.
    names = user.get_all_permissions() if user.is_active and not user.is_superuser else set()
    return TemplateResponse(
        request,
        "accounts/users/detail.html",
        {
            "account": user,
            "groups": [(group, is_ldap_mirrored(group)) for group in user.groups.order_by("name")],
            "permissions": [p for p in own_permissions() if permission_name(p.permission) in names],
            "tenants": get_user_tenants(user),
            "ldap": bool(getattr(settings, "AUTH_LDAP_SERVER_URI", None)),
            "can_change": _may_change_active(request.user, user),
            "next_url": get_redirect_url(request) or reverse("accounts:users"),
        },
    )


@require_POST
@htmx_permission_required("accounts.change_customuser")
def set_active(request, pk):
    """
    Deactivate or reactivate an account; the form posts the state it wants, so
    a repeated request cannot invert it.
    """
    user = get_object_or_404(CustomUser, pk=pk)
    if not _may_change_active(request.user, user):
        raise PermissionDenied(_("You cannot deactivate your own account, nor a superuser unless you are one."))
    active = request.POST.get("active") == "1"

    if user.is_active != active:
        user.is_active = active
        user.save(update_fields=["is_active"])
        JournalEntry.objects.log(
            source="accounts.users",
            event="reactivated" if active else "deactivated",
            summary=f"{'Reactivated' if active else 'Deactivated'} user: {user}",
            user=request.user,
            subject=user,
        )
    message = _("User “%(user)s” was reactivated.") if active else _("User “%(user)s” was deactivated.")
    messages.success(request, message % {"user": user})
    # Back to the user's page, which posts itself as next.
    return redirect(get_redirect_url(request) or reverse("accounts:user_detail", args=[user.pk]))


def _may_change_active(editor, user):
    """
    Not one's own account: deactivated, it would lose its session. Not a
    superuser's, unless the editor is one: no locking out the operators.
    """
    return (
        editor.has_perm("accounts.change_customuser")
        and user != editor
        and (editor.is_superuser or not user.is_superuser)
    )
