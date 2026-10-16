# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Related links: buttons next to a form's select that open the selected object or
add a new one.

The admin puts change, add and view links next to a foreign-key select
(``RelatedFieldWidgetWrapper``). The frontend does the same without the popup:
✎ opens the selected object's page (👁 for a user who may only view it), + its
add page. Both pass the form's page as ``?next=``, so Save and Cancel there
return to the form; an add also passes ``next_field``, and the form then
preselects the new object (``theme.navigation.get_redirect_url_after_add``).

The pages belong to other apps (master data to assets, rooms, persons), so the
owning app registers them here in ``AppConfig.ready()``: the same reason as for
``theme.pickers``. A form calls ``add_related_links`` from its ``__init__``, or a
view after building the form, like ``theme.forms.add_bootstrap_classes``.
"""

from dataclasses import dataclass

from django import forms
from django.contrib.auth import get_permission_codename
from django.db.models import Model
from django.urls import reverse
from django.utils.http import urlencode

from .navigation import with_next
from .widgets import TomSelectMultipleWidget, TomSelectWidget


@dataclass(frozen=True)
class RelatedPages:
    """The frontend pages of a model a select can point to."""

    model: type[Model]
    detail_url: str  # URL name taking the pk, e.g. "assets:manufacturer_detail"
    add_url: str  # URL name of the add page

    def permission(self, action) -> str:
        """The model's default ``action`` permission: the one its pages check."""
        opts = self.model._meta
        return f"{opts.app_label}.{get_permission_codename(action, opts)}"


@dataclass(frozen=True)
class RelatedLinks:
    """
    What the buttons of one select lead to, for one request. Kept on the widget
    by ``add_related_links``, because a widget template has no request and no
    ``perms``.
    """

    pages: RelatedPages
    origin: str  # the form's page, the buttons' ?next=
    can_view: bool
    can_change: bool
    can_add: bool
    # A form re-rendered after a failed save: all its input is unsaved.
    form_is_bound: bool

    def context(self, name, selected, *, multiple):
        """
        The widget template's ``related``. ``name`` is the select's HTML name,
        ``selected`` the values of its selected options. A multi-select gets no
        detail button: it would not know which of its objects to open.
        """
        detail_href_template = detail_href = None
        if self.can_view and not multiple:
            detail_href_template = with_next(reverse(self.pages.detail_url, args=[0]), self.origin)
            if selected:
                detail_href = with_next(reverse(self.pages.detail_url, args=[selected[0]]), self.origin)

        add_href = None
        if self.can_add:
            add_href = with_next(f"{reverse(self.pages.add_url)}?{urlencode({'next_field': name})}", self.origin)

        return {
            "verbose_name": self.pages.model._meta.verbose_name,
            "detail_href_template": detail_href_template,
            "detail_href": detail_href,
            "can_change": self.can_change,
            "add_href": add_href,
            "form_is_bound": self.form_is_bound,
        }


_REGISTRY: dict[str, RelatedPages] = {}


def register_related_pages(pages: RelatedPages) -> None:
    """Register (or replace) the pages of ``pages.model``."""
    _REGISTRY[pages.model._meta.label_lower] = pages


def get_related_pages(model) -> RelatedPages | None:
    """Return the registered pages of ``model``, or ``None``."""
    return _REGISTRY.get(model._meta.label_lower)


def add_related_links(form, request):
    """
    Give the searchable selects of ``form`` their buttons, and preselect an
    object passed in the query string.

    A field gets buttons if it is a model choice field rendered by a TomSelect
    widget, its model has registered pages, and the user may open at least one
    of them: ✎ needs the view and change permissions, 👁 the view permission, +
    the add permission.

    On an unbound form, ``?<field>=<pk>`` (the HTML name, as an add page returns
    it) preselects that object, if it is one the select offers. A multi-select
    adds it to its selection.
    """
    for name, field in form.fields.items():
        if not isinstance(field, forms.ModelChoiceField):
            continue
        if not isinstance(field.widget, (TomSelectWidget, TomSelectMultipleWidget)):
            continue
        model = field.queryset.model
        # Our pages take a pk; a select keyed by another field cannot use them.
        # A model form's foreign key names the pk itself here.
        if field.to_field_name not in (None, model._meta.pk.name):
            continue
        pages = get_related_pages(model)
        if pages is None:
            continue

        user = request.user
        can_view = user.has_perm(pages.permission("view"))
        links = RelatedLinks(
            pages=pages,
            origin=request.get_full_path(),
            can_view=can_view,
            can_change=can_view and user.has_perm(pages.permission("change")),
            can_add=user.has_perm(pages.permission("add")),
            form_is_bound=form.is_bound,
        )
        # A multi-select has no detail button (see RelatedLinks.context).
        if not (links.can_add or (links.can_view and not field.widget.allow_multiple_selected)):
            continue
        field.widget.related = links

        if not form.is_bound:
            _preselect(form, name, field, request)


def _preselect(form, name, field, request):
    """Make ``?<field>=<pk>`` the field's initial value, if the select offers that object."""
    pk = request.GET.get(form.add_prefix(name), "")
    # ASCII digits only: "²" passes isdigit() and fails the query.
    if not (pk.isascii() and pk.isdigit()) or not field.queryset.filter(pk=pk).exists():
        return
    value = pk
    if isinstance(field, forms.ModelMultipleChoiceField):
        selected = [str(getattr(initial, "pk", initial)) for initial in form.get_initial_for_field(field, name) or []]
        value = selected if pk in selected else [*selected, pk]
    # A new dict: ``form.initial`` may be the caller's own.
    form.initial = {**form.initial, name: value}
