# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The list, add, edit and delete pages of one model, after Wagtail's ModelViewSet
(https://docs.wagtail.org/en/stable/reference/viewsets.html#modelviewset): its
names and structure, on Django's generic views and the theme's helpers
(filterbar, pagination, similar names, ``?next=``).

An app subclasses ``ModelViewSet`` and includes its URLs in its ``urls.py``::

    path("things/", include(ThingViewSet().urls)),

which gives ``smallstuff:thing:index``, ``…:add``, ``…:edit`` and ``…:delete``. The
menu entry stays in the app's ``navigation.py``. A page changes through its view
class, its template or what its view gets (``edit_view_class``,
``edit_template_name``, ``get_edit_view_kwargs``).

Each page needs the model's view, add or delete permission. Without the change
permission the edit page shows the form disabled and refuses its POST. An object
that a PROTECT relation keeps can't be deleted: the delete page lists what keeps it.
``delete_view_class = None`` leaves the delete page out; ``history_view_class =
HistoryView`` adds a field history page for a model with django-simple-history.
"""

from collections import defaultdict
from dataclasses import dataclass

import django_filters
from django.contrib.auth import get_permission_codename
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db import router
from django.db.models import Q
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.urls import path, reverse
from django.utils.functional import cached_property
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import generic

from dlcdb.core.models.abstracts import AuditBaseModel
from dlcdb.core.utils.htmx import htmx_permission_required, missing_permission_message
from dlcdb.core.utils.links import detail_url, linked_message

from .field_history import build_field_history
from .filterbar import bind_filterset, build_filterbar
from .forms import disable_fields
from .navigation import detail_urls, get_redirect_url, get_redirect_url_after_add
from .pagination import paginate
from .similar import add_similar_suggestions, similar_context, similar_suggestions


def permission(model, action):
    """The model's default ``action`` permission, e.g. ``smallstuff.change_thing``."""
    opts = model._meta
    return f"{opts.app_label}.{get_permission_codename(action, opts)}"


def _stamp_user(obj, user):
    if isinstance(obj, AuditBaseModel):
        obj.stamp_user(user)


# The most objects the delete page lists per model; it counts them all.
MAX_PROTECTED_LISTED = 10


def protected_objects(obj, user):
    """
    What keeps ``obj`` from being deleted, by model, for the delete page: Django's
    own deletion check (PROTECT, RESTRICT), as in the admin, without deleting.
    Each group counts its objects and lists the first ones, linked to their pages
    where ``user`` may view them. A row of a link table (a many-to-many's
    ``through``) stands for the object on its other side: a position is held by
    persons, not by PersonPosition rows.
    """
    try:
        Collector(using=router.db_for_write(type(obj))).collect([obj])
    except ProtectedError as error:
        blocking = error.protected_objects
    except RestrictedError as error:
        blocking = error.restricted_objects
    else:
        return []

    rows_by_model = defaultdict(list)
    for row in blocking:
        rows_by_model[type(row)].append(row)

    groups = []
    for model, rows in rows_by_model.items():
        link = _link_table_field(model)
        shown = [getattr(row, link.name) if link else row for row in sorted(rows, key=lambda row: row.pk)]
        shown_model = link.related_model if link else model
        may_view = user.has_perm(permission(shown_model, "view"))
        groups.append(
            {
                "label": capfirst(shown_model._meta.verbose_name_plural),
                "count": len(rows),
                "more": max(len(rows) - MAX_PROTECTED_LISTED, 0),
                "entries": [
                    {
                        "label": str(item),
                        "url": detail_url(item) if may_view else None,
                        "deactivated": getattr(item, "deleted_at", None) is not None,
                    }
                    for item in shown[:MAX_PROTECTED_LISTED]
                ],
            }
        )
    return groups


def _link_table_field(model):
    """The foreign key of a link table to the model whose many-to-many runs through it, or None."""
    for field in model._meta.fields:
        if field.many_to_one and any(
            m2m.remote_field.through is model for m2m in field.related_model._meta.many_to_many
        ):
            return field
    return None


@dataclass(frozen=True)
class Column:
    """
    An index column: an attribute of the rows, its heading, its sort key, its CSS
    classes, and the template of its cells (with ``object`` and ``value``), as in
    Wagtail; without one a cell shows the value.
    """

    name: str
    label: str
    sort_key: str = ""
    classname: str = ""
    cell_template_name: str = ""


@dataclass(frozen=True)
class Usage:
    """
    The edit page's usage card: how many use the object (an annotation of the
    viewset's queryset), linked to the list that ``filter`` narrows to them, for
    users with that list's view ``permission``.
    """

    label: str
    count: str
    list_url_name: str
    filter: str
    permission: str
    icon: str = ""


class SearchFilterSet(django_filters.FilterSet):
    """The index's search box: a row matches when one of ``search_fields`` contains the term."""

    search = django_filters.CharFilter(method="filter_search", label=gettext_lazy("Search"))
    search_fields = ()

    def filter_search(self, queryset, name, value):
        matches = Q()
        for field in self.search_fields:
            matches |= Q(**{f"{field}__icontains": value})
        return queryset.filter(matches)


class ModelViewMixin:
    """What the pages of a viewset share: its model, its icon and its URLs."""

    header_icon = ""

    def url_name(self, view_name):
        """A URL name of this viewset: its namespace nests in the app's (``smallstuff:thing``)."""
        return f"{self.request.resolver_match.namespace}:{view_name}"

    def has_permission(self, action):
        return self.request.user.has_perm(permission(self.model, action))

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            opts=self.model._meta,
            header_icon=self.header_icon,
            # Only an AuditBaseModel has the data of the audit card.
            audited=issubclass(self.model, AuditBaseModel),
            **kwargs,
        )


class IndexView(ModelViewMixin, generic.ListView):
    template_name = "theme/viewsets/index.html"
    list_display = ()
    # A subclass of SearchFilterSet adds the model's own filters, as in Wagtail.
    filterset_class = SearchFilterSet
    search_fields = ()
    search_placeholder = ""
    list_per_page = 25

    @cached_property
    def columns(self):
        return [entry if isinstance(entry, Column) else self._field_column(entry) for entry in self.list_display]

    def _field_column(self, name):
        if name == "__str__":
            return Column(name, capfirst(self.model._meta.verbose_name))
        return Column(name, capfirst(self.model._meta.get_field(name).verbose_name), sort_key=name)

    def get_filterset_class(self):
        """``filterset_class``, with the search fields and the sort keys of the columns and their headings."""
        sort_keys = {column.sort_key: column.label for column in self.columns if column.sort_key}
        ordering = django_filters.OrderingFilter(fields=[(key, key) for key in sort_keys], field_labels=sort_keys)
        return type(
            "IndexFilterSet", (self.filterset_class,), {"search_fields": self.search_fields, "ordering": ordering}
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        self.total_count = queryset.count()
        self.filterset = bind_filterset(
            self.get_filterset_class(), self.request, queryset, default_ordering=self.ordering or ""
        )
        return self.filterset.qs

    def get_template_names(self):
        # Searching, sorting and paging swap only the list.
        return [f"{self.template_name}#object-list" if self.request.htmx else self.template_name]

    def cells(self, obj):
        """One row: each column with its value; the template can't look attributes up by name."""
        return [
            (column, str(obj) if column.name == "__str__" else getattr(obj, column.name)) for column in self.columns
        ]

    def get_context_data(self, **kwargs):
        page_obj = paginate(self.request, self.object_list, self.list_per_page)
        return super().get_context_data(
            page_obj=page_obj,
            columns=self.columns,
            rows=[(obj, self.cells(obj)) for obj in page_obj],
            filterbar=build_filterbar(
                self.filterset, self.request, target="#object-list", search_placeholder=self.search_placeholder
            ),
            current_ordering=self.filterset.data["ordering"],
            filtered_count=page_obj.paginator.count,
            total_count=self.total_count,
            edit_url_name=self.url_name("edit"),
            add_url=reverse(self.url_name("add")) if self.has_permission("add") else None,
            **kwargs,
        )


class CreateView(ModelViewMixin, SuccessMessageMixin, generic.CreateView):
    template_name = "theme/viewsets/create.html"
    form_fields_template = "theme/viewsets/_form_fields.html"
    success_message = gettext_lazy("%(model)s “%(obj)s” was created.")

    def get(self, request, *args, **kwargs):
        if request.htmx and hasattr(self.form_class, "similar_names"):
            # The name being typed: list the similar existing entries.
            return similar_suggestions(request, self.form_class)
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        """Form fields preset from the query string, as on the admin's add page: ``?device_type=3``."""
        fields = self.get_form_class().base_fields
        return {**super().get_initial(), **{name: value for name, value in self.request.GET.items() if name in fields}}

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if hasattr(form, "similar_names"):
            add_similar_suggestions(form, self.request)
        return form

    def form_valid(self, form):
        _stamp_user(form.instance, self.request.user)
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return self.success_message % {"model": self.model._meta.verbose_name, "obj": self.object}

    def get_success_url(self):
        # The page that opened this one (a form's + button, say) comes as ?next=:
        # back there with the new object. Cancel leads there without it.
        return get_redirect_url_after_add(self.request, self.object.pk) or reverse(
            self.url_name("edit"), args=[self.object.pk]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            next_url=get_redirect_url(self.request) or reverse(self.url_name("index")),
            form_fields_template=self.form_fields_template,
            **kwargs,
        )
        # Existing entries the new one may duplicate, after a refused save.
        context["similar"] = similar_context(self.request, getattr(context["form"], "similar_matches", None))
        return context


class EditView(ModelViewMixin, SuccessMessageMixin, generic.UpdateView):
    """Read and edit one object; without the change permission the form is disabled."""

    template_name = "theme/viewsets/edit.html"
    form_fields_template = "theme/viewsets/_form_fields.html"
    usage = None
    # False when the viewset leaves the delete page out.
    delete_enabled = True
    history_enabled = False

    def post(self, request, *args, **kwargs):
        if not self.has_permission("change"):
            raise PermissionDenied(missing_permission_message(permission(self.model, "change")))
        return super().post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.has_permission("change"):
            disable_fields(form)
        return form

    def form_valid(self, form):
        _stamp_user(form.instance, self.request.user)
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return linked_message(_("{model} “{obj}” was updated."), model=self.model._meta.verbose_name, obj=self.object)

    def detail_urls(self):
        """Where Back, Cancel and Save lead (``?next=``, else the index), and the form's action, which keeps it."""
        return detail_urls(self.request, self.url_name("index"), self.url_name("edit"), self.object.pk)

    def get_success_url(self):
        return self.detail_urls()[0]

    def usage_card(self):
        if self.usage is None:
            return None
        count = getattr(self.object, self.usage.count)
        url = None
        if count and self.request.user.has_perm(self.usage.permission):
            url = f"{reverse(self.usage.list_url_name)}?{self.usage.filter}={self.object.pk}"
        return {"label": self.usage.label, "icon": self.usage.icon, "count": count, "url": url}

    def get_context_data(self, **kwargs):
        next_url, form_action = self.detail_urls()
        return super().get_context_data(
            can_change=self.has_permission("change"),
            readonly_message=_("You may view this entry but do not have permission to edit it."),
            next_url=next_url,
            form_action=form_action,
            # The Delete link of theme/_form_action_bar.html.
            delete_url=reverse(self.url_name("delete"), args=[self.object.pk])
            if self.delete_enabled and self.has_permission("delete")
            else None,
            usage=self.usage_card(),
            history_url=reverse(self.url_name("history"), args=[self.object.pk]) if self.history_enabled else None,
            form_fields_template=self.form_fields_template,
            **kwargs,
        )


class DeleteView(ModelViewMixin, SuccessMessageMixin, generic.DeleteView):
    """Confirm, then delete; an object a PROTECT relation keeps lists what keeps it instead."""

    template_name = "theme/viewsets/confirm_delete.html"
    success_message = gettext_lazy("%(model)s “%(obj)s” was deleted.")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (ProtectedError, RestrictedError):
            # Taken into use since the page was shown: now it says so.
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_message(self, cleaned_data):
        return self.success_message % {"model": self.model._meta.verbose_name, "obj": self.object}

    def get_success_url(self):
        return reverse(self.url_name("index"))

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            protected=protected_objects(self.object, self.request.user),
            edit_url=reverse(self.url_name("edit"), args=[self.object.pk]),
            **kwargs,
        )


class HistoryView(ModelViewMixin, generic.DetailView):
    """When who changed which field (django-simple-history), as Wagtail's history page."""

    template_name = "theme/viewsets/history.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            entries=build_field_history(self.object),
            edit_url=reverse(self.url_name("edit"), args=[self.object.pk]),
            **kwargs,
        )


class ModelViewSet:
    """The pages of one model; a subclass sets the model and what differs (see the module docstring)."""

    model = None
    form_class = None
    list_display = ("__str__",)
    filterset_class = None
    search_fields = ()
    search_placeholder = ""
    ordering = None
    list_per_page = 25
    icon = ""
    usage = None
    # Defaults to the model name.
    url_namespace = None

    index_view_class = IndexView
    add_view_class = CreateView
    edit_view_class = EditView
    # None leaves the delete page out.
    delete_view_class = DeleteView
    # HistoryView adds the field history page.
    history_view_class = None

    # None keeps the view class's template_name.
    index_template_name = None
    create_template_name = None
    edit_template_name = None
    delete_template_name = None
    history_template_name = None
    # The form's fields on the add and edit page, e.g. in cards of their own.
    form_fields_template = None

    def get_queryset(self):
        """What the pages list and load; a subclass annotates its counts here."""
        return self.model._default_manager.all()

    def get_form_class(self, for_update=False):
        return self.form_class

    def construct_view(self, view_class, **kwargs):
        """The view, with what all pages get; a None keeps the view's own default."""
        kwargs = {"model": self.model, "queryset": self.get_queryset(), "header_icon": self.icon, **kwargs}
        return view_class.as_view(**{key: value for key, value in kwargs.items() if value is not None})

    # What each view gets besides what all get, as in Wagtail: a subclass adds to
    # them, e.g. ``extra_context`` for its template.
    def get_index_view_kwargs(self, **kwargs):
        return {
            "template_name": self.index_template_name,
            "list_display": self.list_display,
            "filterset_class": self.filterset_class,
            "search_fields": self.search_fields,
            "search_placeholder": self.search_placeholder,
            "ordering": self.ordering,
            "list_per_page": self.list_per_page,
            **kwargs,
        }

    def get_add_view_kwargs(self, **kwargs):
        return {
            "template_name": self.create_template_name,
            "form_class": self.get_form_class(),
            "form_fields_template": self.form_fields_template,
            **kwargs,
        }

    def get_edit_view_kwargs(self, **kwargs):
        return {
            "template_name": self.edit_template_name,
            "form_class": self.get_form_class(for_update=True),
            "form_fields_template": self.form_fields_template,
            "usage": self.usage,
            "delete_enabled": self.delete_view_class is not None,
            "history_enabled": self.history_view_class is not None,
            **kwargs,
        }

    def get_delete_view_kwargs(self, **kwargs):
        return {"template_name": self.delete_template_name, **kwargs}

    def get_history_view_kwargs(self, **kwargs):
        return {"template_name": self.history_template_name, **kwargs}

    @property
    def index_view(self):
        return self.construct_view(self.index_view_class, **self.get_index_view_kwargs())

    @property
    def add_view(self):
        return self.construct_view(self.add_view_class, **self.get_add_view_kwargs())

    @property
    def edit_view(self):
        return self.construct_view(self.edit_view_class, **self.get_edit_view_kwargs())

    @property
    def delete_view(self):
        return self.construct_view(self.delete_view_class, **self.get_delete_view_kwargs())

    @property
    def history_view(self):
        return self.construct_view(self.history_view_class, **self.get_history_view_kwargs())

    def get_urlpatterns(self):
        """
        The pages, each behind the model's permission; the guard records it for
        the group pages. The edit page checks the change permission itself.
        """

        def guarded(action, view):
            return htmx_permission_required(permission(self.model, action))(view)

        patterns = [
            path("", guarded("view", self.index_view), name="index"),
            path("new/", guarded("add", self.add_view), name="add"),
            path("edit/<int:pk>/", guarded("view", self.edit_view), name="edit"),
        ]
        if self.delete_view_class is not None:
            patterns.append(path("delete/<int:pk>/", guarded("delete", self.delete_view), name="delete"))
        if self.history_view_class is not None:
            patterns.append(path("history/<int:pk>/", guarded("view", self.history_view), name="history"))
        return patterns

    @property
    def urls(self):
        """The patterns in the viewset's namespace, for ``include()`` in the app's ``urls.py``."""
        return self.get_urlpatterns(), self.url_namespace or self.model._meta.model_name
