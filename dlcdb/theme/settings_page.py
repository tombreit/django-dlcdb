# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The settings pages of the gear menu that edit a ``SingletonBaseModel``
(``dlcdb/core/models/abstracts.py``): one form on the model's one row.

The app's view checks the view permission and calls ``settings_page``; saving
needs the model's change permission. Without it every field is disabled, so the
page shows the same form read-only. ``theme/_settings_base.html`` is the frame.

Pure function, no view class or mixin — the same convention as ``paginate``.
"""

from django.contrib import messages
from django.contrib.auth import get_permission_codename
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import translation
from django.utils.text import capfirst
from django.utils.translation import gettext as _

from dlcdb.core.utils.htmx import missing_permission_message
from dlcdb.journal.models import JournalEntry

from .forms import disable_fields
from .navigation import get_redirect_url, with_next


def settings_page(request, form_class, *, icon, template="theme/_settings_base.html", context=None):
    """
    Show and save the one row of ``form_class``'s model. The page's title is
    the model's verbose name; ``icon`` is the bi icon class of its card.

    A save returns to this page, or to ``?next=``, and journals which fields
    changed. Pages with more than the form pass their own ``template`` (extending
    ``theme/_settings_base.html``) and its extra ``context``.
    """
    opts = form_class._meta.model._meta
    config = form_class._meta.model.load()
    change_permission = f"{opts.app_label}.{get_permission_codename('change', opts)}"
    can_change = request.user.has_perm(change_permission)
    title = capfirst(opts.verbose_name)
    redirect_to = get_redirect_url(request)

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied(missing_permission_message(change_permission))
        form = form_class(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            if form.has_changed():
                _journal_changes(form, config, user=request.user)
            messages.success(request, _("%(settings)s saved.") % {"settings": title})
            return redirect(redirect_to or request.path)
    else:
        form = form_class(instance=config)
        if not can_change:
            disable_fields(form)

    return TemplateResponse(
        request,
        template,
        {
            "form": form,
            "title": title,
            "icon": icon,
            "can_change": can_change,
            # Back, Cancel and Save of theme/_detail_base.html.
            "next_url": redirect_to or request.path,
            "form_action": with_next(request.path, redirect_to),
            **(context or {}),
        },
    )


def _journal_changes(form, config, *, user):
    """One journal entry naming the changed fields: never their values, the HR token is one."""
    # Journal text is data, in English, like the other journal entries.
    # capfirst() keeps a lazy name lazy: render it here, not in the f-string below.
    with translation.override(None):
        settings_name = str(capfirst(config._meta.verbose_name))
        fields = ", ".join(str(form.fields[name].label) for name in form.changed_data)
    JournalEntry.objects.log(
        source=f"{config._meta.app_label}.settings",
        event="changed",
        summary=f"{settings_name} changed: {fields}",
        user=user,
        subject=config,
    )
