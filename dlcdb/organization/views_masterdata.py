# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The organizational units and the positions persons hold. Settings › Organization
lists them (organization/branding.html); these are their add, edit and delete
pages. Both are a name only, so one set of views serves both, parameterized by
a ``Kind``, like the device master data (assets/views/masterdata.py). Global,
like device types: no tenant scoping.
"""

from dataclasses import dataclass

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, ProtectedError, Q
from django.forms import ModelForm
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit, Person
from dlcdb.core.utils.htmx import htmx_permission_required, missing_permission_message
from dlcdb.core.utils.links import linked_message
from dlcdb.theme.navigation import get_redirect_url, get_redirect_url_after_add, with_next
from dlcdb.theme.similar import add_similar_suggestions, similar_context, similar_suggestions

from .forms import OrganizationalPositionForm, OrganizationalUnitForm


@dataclass(frozen=True)
class Kind:
    """Everything that differs between units and positions."""

    model: type
    form_class: type[ModelForm]
    add_route: str
    detail_route: str
    delete_route: str
    # The id of its card on the Organization page.
    anchor: str
    # The query name from the model to its persons, and the persons list
    # filter: Person.organizational_unit has no related_name.
    persons_lookup: str
    persons_filter: str
    icon: str
    add_title: str
    submit_label: str

    @property
    def verbose_name(self):
        """For templates, which can't reach ``_meta``."""
        return self.model._meta.verbose_name

    def permission(self, action):
        return f"core.{action}_{self.model._meta.model_name}"

    def cards_url(self):
        """Its card on the Organization page, opened by organization/js/contents.js."""
        return f"{reverse('organization:branding')}#{self.anchor}"

    def rows(self):
        """
        All entries, each with the number of its active persons, as the persons
        list counts them. Ordered here: a counting query ignores Meta.ordering.
        """
        active = Q(**{f"{self.persons_lookup}__deleted_at__isnull": True})
        return self.model.objects.annotate(persons_count=Count(self.persons_lookup, filter=active)).order_by("name")

    def persons(self, obj):
        """The persons holding ``obj``, deactivated ones included: they protect it too."""
        return Person.with_softdeleted_objects.filter(**{self.persons_filter: obj})


UNIT = Kind(
    model=OrganizationalUnit,
    form_class=OrganizationalUnitForm,
    add_route="organization:unit_add",
    detail_route="organization:unit_detail",
    delete_route="organization:unit_delete",
    anchor="units",
    persons_lookup="person",
    persons_filter="organizational_unit",
    icon="bi-diagram-3",
    add_title=gettext_lazy("Add organizational unit"),
    submit_label=gettext_lazy("Create organizational unit"),
)

POSITION = Kind(
    model=OrganizationalPosition,
    form_class=OrganizationalPositionForm,
    add_route="organization:position_add",
    detail_route="organization:position_detail",
    delete_route="organization:position_delete",
    anchor="positions",
    persons_lookup="persons",
    persons_filter="organizational_positions",
    icon="bi-person-badge",
    add_title=gettext_lazy("Add position"),
    submit_label=gettext_lazy("Create position"),
)


def _add(request, kind):
    if request.htmx:
        # The name being typed: list the similar existing entries.
        return similar_suggestions(request, kind.form_class)
    form = kind.form_class(request.POST or None)
    add_similar_suggestions(form, request)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.stamp_user(request.user)
        obj.save()
        messages.success(request, _("%(model)s “%(obj)s” was created.") % {"model": kind.verbose_name, "obj": obj})
        # A person form's + button comes as ?next=: back there with the new entry.
        return redirect(get_redirect_url_after_add(request, obj.pk) or kind.cards_url())

    return TemplateResponse(
        request,
        "organization/name_form.html",
        {
            "form": form,
            "kind": kind,
            "next_url": get_redirect_url(request) or kind.cards_url(),
            # Existing entries the new one may duplicate, after a refused save.
            "similar": similar_context(request, getattr(form, "similar_matches", None)),
        },
    )


def _detail(request, kind, pk):
    """Read and edit one entry; without the change permission the name is disabled."""
    obj = get_object_or_404(kind.model, pk=pk)
    can_change = request.user.has_perm(kind.permission("change"))
    next_url = get_redirect_url(request) or kind.cards_url()

    if request.method == "POST":
        if not can_change:
            raise PermissionDenied(missing_permission_message(kind.permission("change")))
        form = kind.form_class(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.stamp_user(request.user)
            obj.save()
            messages.success(
                request, linked_message(_("{model} “{obj}” was updated."), model=kind.verbose_name, obj=obj)
            )
            return redirect(next_url)
    else:
        form = kind.form_class(instance=obj)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return TemplateResponse(
        request,
        "organization/name_detail.html",
        {
            "object": obj,
            "kind": kind,
            "form": form,
            "can_change": can_change,
            "next_url": next_url,
            "form_action": with_next(reverse(kind.detail_route, args=[obj.pk]), get_redirect_url(request)),
            "persons_count": kind.persons(obj).filter(deleted_at__isnull=True).count(),
            "persons_url": f"{reverse('persons:index')}?{kind.persons_filter}={obj.pk}",
            # The Delete link of theme/_form_action_bar.html.
            "delete_url": (
                reverse(kind.delete_route, args=[obj.pk]) if request.user.has_perm(kind.permission("delete")) else None
            ),
        },
    )


def _delete(request, kind, pk):
    """
    Confirm, then delete. An entry somebody holds, a deactivated person
    included, is protected (on_delete=PROTECT): the page says so instead.
    """
    obj = get_object_or_404(kind.model, pk=pk)
    persons = kind.persons(obj)
    if request.method == "POST" and not persons.exists():
        try:
            obj.delete()
        except ProtectedError:
            pass  # Assigned meanwhile: the page below says so.
        else:
            messages.success(request, _("%(model)s “%(obj)s” was deleted.") % {"model": kind.verbose_name, "obj": obj})
            return redirect(kind.cards_url())
    return TemplateResponse(
        request,
        "organization/name_delete.html",
        {
            "object": obj,
            "kind": kind,
            "persons_count": persons.filter(deleted_at__isnull=True).count(),
            "deactivated_count": persons.filter(deleted_at__isnull=False).count(),
        },
    )


@htmx_permission_required("core.add_organizationalunit")
def unit_add(request):
    return _add(request, UNIT)


@htmx_permission_required("core.view_organizationalunit")
def unit_detail(request, pk):
    return _detail(request, UNIT, pk)


@htmx_permission_required("core.delete_organizationalunit")
def unit_delete(request, pk):
    return _delete(request, UNIT, pk)


@htmx_permission_required("core.add_organizationalposition")
def position_add(request):
    return _add(request, POSITION)


@htmx_permission_required("core.view_organizationalposition")
def position_detail(request, pk):
    return _detail(request, POSITION, pk)


@htmx_permission_required("core.delete_organizationalposition")
def position_delete(request, pk):
    return _delete(request, POSITION, pk)
