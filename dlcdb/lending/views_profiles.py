# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The lending profiles: one per device type, with the lending slip template, the
preparation checklist and the regulations. Settings › Lending configuration
lists them; these are their add and edit pages. Profiles are global, like device
types: no tenant scoping.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _

from dlcdb.core.utils.htmx import htmx_permission_required, missing_permission_message
from dlcdb.core.utils.links import linked_message, obj_link
from dlcdb.theme.field_history import build_field_history
from dlcdb.theme.navigation import detail_urls, get_redirect_url

from .forms import LendingProfileForm
from .models import LendingProfile
from .starter import restore_empty


def _save(request, form):
    """Save the profile; an emptied slip template or checklist gets the starter content again."""
    profile = form.save(commit=False)
    for field in restore_empty(profile):
        messages.info(request, _("“%(field)s” was empty and holds the starter content again.") % {"field": field})
    profile.save()
    form.save_m2m()
    return profile


@htmx_permission_required("lending.add_lendingprofile")
def profile_add(request):
    """``?device_type=`` preselects the type: the lending page's "Add one?" passes it."""
    form = LendingProfileForm(request.POST or None, initial={"device_type": request.GET.get("device_type")})
    if request.method == "POST" and form.is_valid():
        profile = _save(request, form)
        messages.success(request, _("Lending profile for “%(type)s” was created.") % {"type": profile.device_type})
        return redirect(get_redirect_url(request) or reverse("lending:profile_detail", args=[profile.pk]))

    return TemplateResponse(
        request,
        "lending/profile_form.html",
        {"form": form, "next_url": get_redirect_url(request) or reverse("lending:configuration")},
    )


@htmx_permission_required("lending.view_lendingprofile")
def profile_detail(request, pk):
    """Read and edit one profile; without the change permission the same fields are disabled."""
    profile = get_object_or_404(LendingProfile.objects.select_related("device_type"), pk=pk)
    can_change = request.user.has_perm("lending.change_lendingprofile")
    next_url, form_action = detail_urls(request, "lending:configuration", "lending:profile_detail", profile.pk)

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied(missing_permission_message("lending.change_lendingprofile"))
        form = LendingProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = _save(request, form)
            messages.success(
                request,
                linked_message(
                    _("Lending profile for “{type}” was updated."), type=obj_link(profile, label=profile.device_type)
                ),
            )
            return redirect(next_url)
    else:
        form = LendingProfileForm(instance=profile)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return TemplateResponse(
        request,
        "lending/profile_detail.html",
        {
            "profile": profile,
            "form": form,
            "can_change": can_change,
            "next_url": next_url,
            "form_action": form_action,
            # The Delete link of theme/_form_action_bar.html.
            "delete_url": (
                reverse("lending:profile_delete", args=[profile.pk])
                if request.user.has_perm("lending.delete_lendingprofile")
                else None
            ),
        },
    )


@htmx_permission_required("lending.delete_lendingprofile")
def profile_delete(request, pk):
    """Confirm, then delete; the profile history keeps the deletion."""
    profile = get_object_or_404(LendingProfile.objects.select_related("device_type"), pk=pk)
    if request.method == "POST":
        profile.delete()
        messages.success(request, _("Lending profile for “%(type)s” was deleted.") % {"type": profile.device_type})
        return redirect("lending:configuration")
    return TemplateResponse(request, "lending/profile_delete.html", {"profile": profile})


@htmx_permission_required("lending.view_lendingprofile")
def profile_history(request, pk):
    """When who changed which field of one profile (django-simple-history); the regulations are not tracked."""
    profile = get_object_or_404(LendingProfile.objects.select_related("device_type"), pk=pk)
    return TemplateResponse(
        request, "lending/profile_history.html", {"profile": profile, "entries": build_field_history(profile)}
    )
