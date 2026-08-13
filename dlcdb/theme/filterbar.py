# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Reusable search/filter/sort bar ("filterbar") for django-filter list views.

Usage: a list view builds the bar from its FilterSet and puts it into the
template context ...

    context["filterbar"] = build_filterbar(
        my_filterset, request, target="#my-list", search_placeholder=_("Search...")
    )

... and the templates render it with plain includes:

    {% include "theme/filterbar/filterbar.html" with bar=filterbar %}
    {# inside the HTMX-swapped list fragment: #}
    {% include "theme/filterbar/chips.html" with bar=filterbar %}

The bar is derived by introspecting the FilterSet: the filter named
``search_field`` becomes the search input, an OrderingFilter becomes the sort
dropdown, choice-ish filters become one dropdown each. Everything is plain
data (frozen dataclasses of strings) — no state, no template tags, no mixins.

A sort counts as a user modification of the viewset, exactly like a filter: it
gets its own removable chip and "Clear all" undoes it. What separates "the page
is sorted" from "the user sorted it" is whether ``?ordering=`` is in the
request — the bar reads the selection from ``request.GET``, not from the
FilterSet's data, which every view has already seeded with its own default.

Conventions the consuming view/page must follow:
- the list page is served at its own endpoint (the form submits to
  ``request.path``),
- exactly one filterbar per page,
- the HTMX-swapped fragment root carries hx-target/hx-swap/hx-push-url so the
  sortable column headers (``_sort_th.html``) can inherit them,
- the view injects its default ordering onto a copy of ``request.GET``
  (``data.setdefault("ordering", ...)``). This is load-bearing, not advisory:
  "Clear all" drops ``?ordering=`` and django-filter leaves the queryset
  untouched for an empty ordering, so a view without that default would
  paginate an unordered queryset.
"""

from dataclasses import dataclass

import django_filters
from django.utils.translation import gettext as _


@dataclass(frozen=True)
class FilterSpec:
    """One filter rendered as a dropdown in the bar."""

    param: str  # GET parameter name
    label: str
    input_type: str  # "radio" | "checkbox"
    choices: list  # [(value, label, checked)]; the empty value is the radio reset choice
    selected_values: list
    selected_label: str
    multiple: bool


@dataclass(frozen=True)
class Chip:
    """One user-made modification of the viewset, shown as a removable chip."""

    param: str
    value: str
    label: str
    value_label: str
    remove_href: str
    icon: str = ""  # optional Bootstrap icon class rendered after the value
    # Below md the filter and sort dropdowns fold into the offcanvas panel while
    # the search input stays visible, so only the former are worth counting on
    # the "Filters (n)" button that opens it.
    in_panel: bool = True


@dataclass(frozen=True)
class SortOption:
    value: str  # ordering param value, e.g. "-modified"
    label: str
    descending: bool
    selected: bool


@dataclass(frozen=True)
class FilterBar:
    search_param: str  # "" when the FilterSet has no search filter
    search_value: str
    specs: list[FilterSpec]
    secondary_specs: list[FilterSpec]  # demoted filters, tucked behind "More filters"
    secondary_active: bool  # a secondary spec has a selected value -> start expanded
    ordering_param: str  # "" when the FilterSet has no OrderingFilter
    sort_options: list[SortOption]
    current_sort: SortOption | None  # the sort the user picked; None on the view's default
    chips: list[Chip]  # everything the user changed, in display order
    active_count: int  # how many of those sit behind the mobile "Filters (n)" button
    clear_all_href: str
    target: str
    search_placeholder: str
    bar_id: str
    hidden_params: dict  # scope params carried through the bar's form, not rendered as filters


def build_filterbar(
    filterset,
    request,
    *,
    target,
    search_placeholder="",
    search_field="search",
    bar_id="filterbar",
    secondary_fields=(),
    hidden_params=None,
):
    """
    Pure helper: derive a FilterBar from a bound FilterSet and the request's
    GET parameters. Does not touch ``filterset.qs``.

    ``secondary_fields`` names filters to demote into ``secondary_specs`` (a
    "More filters" tier the view considers less important) — the component
    itself has no notion of which filters matter more.

    ``hidden_params`` names GET parameters that scope the whole page rather than
    filter it (``?device=`` on the record trail). The bar is a GET form, so a
    submit replaces the entire query string with the form's own fields: without
    a hidden input the scope would be lost on the first keystroke. They are the
    only parameters "Clear all" keeps, for the same reason — resetting the bar
    must not silently widen the page to a different set of objects.
    """
    hidden_params = hidden_params or {}
    form = filterset.form

    search_param = ""
    search_value = ""
    specs = []
    secondary_specs = []
    ordering_param = ""
    sort_options = []

    for name, flt in filterset.filters.items():
        bound_field = form[name]

        if name == search_field:
            search_param = bound_field.html_name
            search_value = str(bound_field.value() or "")
            continue

        if isinstance(flt, django_filters.OrderingFilter):
            ordering_param = bound_field.html_name
            # From request.GET, not from the bound field: the view seeds its own
            # default into the FilterSet's data, and that default is not a sort
            # the user picked.
            sort_options = _sort_options(bound_field, request.GET.get(ordering_param, ""))
            continue

        spec = _filter_spec(flt, bound_field)
        if spec is not None:
            (secondary_specs if name in secondary_fields else specs).append(spec)

    secondary_active = any(spec.selected_values for spec in secondary_specs)
    current_sort = next((opt for opt in sort_options if opt.selected), None)

    # One list, in the order they read on screen: the search term, then the
    # filters, then the sort.
    chips = []
    if search_value:
        chips.append(_chip(request, search_param, search_value, _("Search"), search_value, in_panel=False))
    chips += [chip for spec in specs + secondary_specs for chip in _spec_chips(spec, request)]
    if current_sort:
        chips.append(
            _chip(
                request,
                ordering_param,
                current_sort.value,
                _("Sort"),
                current_sort.label,
                # The same direction icons the sort dropdown uses, rather than a
                # third vocabulary for "descending".
                icon="bi-sort-down" if current_sort.descending else "bi-sort-up",
            )
        )

    return FilterBar(
        search_param=search_param,
        search_value=search_value,
        specs=specs,
        secondary_specs=secondary_specs,
        secondary_active=secondary_active,
        ordering_param=ordering_param,
        sort_options=sort_options,
        current_sort=current_sort,
        chips=chips,
        active_count=sum(chip.in_panel for chip in chips),
        clear_all_href=_clear_all_href(request, keep_params=set(hidden_params)),
        target=target,
        search_placeholder=search_placeholder,
        bar_id=bar_id,
        hidden_params=hidden_params,
    )


def _filter_spec(flt, bound_field):
    """Classify one filter into a FilterSpec, or None if it has no bar widget."""
    # Explicit tuples instead of the base classes alone: they document intent
    # without requiring the reader to know django-filter's class hierarchy.
    if isinstance(flt, (django_filters.MultipleChoiceFilter, django_filters.ModelMultipleChoiceFilter)):
        multiple, input_type = True, "checkbox"
    elif isinstance(flt, (django_filters.ChoiceFilter, django_filters.ModelChoiceFilter)):
        multiple, input_type = False, "radio"
    else:
        return None

    pairs = [(str(value), str(label)) for value, label in bound_field.field.choices]
    label_by_value = dict(pairs)
    selected_values = [value for value in _raw_values(bound_field) if value in label_by_value and value != ""]
    choices = [(value, label, _is_checked(value, selected_values, multiple)) for value, label in pairs]

    if len(selected_values) == 1:
        selected_label = label_by_value[selected_values[0]]
    elif selected_values:
        selected_label = _("%(count)d selected") % {"count": len(selected_values)}
    else:
        selected_label = ""

    return FilterSpec(
        param=bound_field.html_name,
        label=str(bound_field.label),
        input_type=input_type,
        choices=choices,
        selected_values=selected_values,
        selected_label=selected_label,
        multiple=multiple,
    )


def _is_checked(value, selected_values, multiple):
    if value in selected_values:
        return True
    # The empty radio choice is the dropdown's own reset: checked when nothing is.
    return not multiple and value == "" and not selected_values


def _raw_values(bound_field):
    """The bound field's raw GET value(s), normalized to a list of strings."""
    raw = bound_field.value()
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(value) for value in raw if value not in (None, "")]
    return [str(raw)] if str(raw) else []


def _chip(request, param, value, label, value_label, *, icon="", in_panel=True):
    """One thing the user changed, with the href that undoes it."""
    return Chip(
        param=param,
        value=value,
        label=label,
        value_label=value_label,
        remove_href=_remove_value_href(request, param, value),
        icon=icon,
        in_panel=in_panel,
    )


def _spec_chips(spec, request):
    """One removable chip per selected value; unknown/invalid values yield none."""
    label_by_value = {value: label for value, label, _checked in spec.choices}
    return [_chip(request, spec.param, value, spec.label, label_by_value[value]) for value in spec.selected_values]


def _sort_options(bound_field, current):
    """
    Pair the OrderingFilter's asc/desc choices ("device" / "-device") into
    SortOptions sharing the ascending label; direction is carried as a flag so
    the template can render an icon instead of the "(descending)" suffix.

    ``current`` is the raw ``?ordering=`` value from the request — the sort the
    user picked, which is not the same as the ordering in force: views seed a
    default into the FilterSet's data. Nothing is selected on a default page, so
    the bar shows a plain "Sort" button and no chip until the user sorts.
    """
    if isinstance(current, str):
        current = current.split(",")
    current = current[0].strip() if current else ""

    ascending_labels = {}
    for value, label in bound_field.field.choices:
        value = str(value)
        if value and not value.startswith("-"):
            ascending_labels[value] = str(label)

    options = []
    for value, label in ascending_labels.items():
        options.append(SortOption(value=value, label=label, descending=False, selected=current == value))
        options.append(SortOption(value=f"-{value}", label=label, descending=True, selected=current == f"-{value}"))
    return options


def _remove_value_href(request, param, value):
    """Current URL minus one value of one parameter (multi-value aware)."""
    query = request.GET.copy()
    remaining = [v for v in query.getlist(param) if v != value]
    if remaining:
        query.setlist(param, remaining)
    else:
        query.pop(param, None)
    encoded = query.urlencode()
    return f"{request.path}?{encoded}" if encoded else request.path


def _clear_all_href(request, keep_params):
    """Current URL minus everything the user chose — search, filters *and* the
    ordering: "Clear all" undoes every modification of the viewset, and a custom
    sort is one of them. Dropping ``?ordering=`` lands on the view's own default
    because the view re-injects it; django-filter alone would leave the queryset
    unordered. Only the hidden scope params survive: they say which objects the
    page is about, not how the user narrowed them."""
    query = request.GET.copy()
    for key in list(query.keys()):
        if key not in keep_params:
            del query[key]
    encoded = query.urlencode()
    return f"{request.path}?{encoded}" if encoded else request.path
