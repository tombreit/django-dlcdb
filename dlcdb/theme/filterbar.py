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

Conventions the consuming view/page must follow:
- the list page is served at its own endpoint (the form submits to
  ``request.path``),
- exactly one filterbar per page,
- the HTMX-swapped fragment root carries hx-target/hx-swap/hx-push-url so the
  sortable column headers (``_sort_th.html``) can inherit them.
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
    """One active filter value, shown as a removable chip."""

    param: str
    value: str
    label: str
    value_label: str
    remove_href: str


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
    ordering_param: str  # "" when the FilterSet has no OrderingFilter
    sort_options: list[SortOption]
    current_sort: SortOption | None
    chips: list[Chip]
    clear_all_href: str
    target: str
    search_placeholder: str
    bar_id: str


def build_filterbar(
    filterset,
    request,
    *,
    target,
    search_placeholder="",
    search_field="search",
    bar_id="filterbar",
):
    """
    Pure helper: derive a FilterBar from a bound FilterSet and the request's
    GET parameters. Does not touch ``filterset.qs``.
    """
    form = filterset.form

    search_param = ""
    search_value = ""
    specs = []
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
            sort_options = _sort_options(bound_field)
            continue

        spec = _filter_spec(flt, bound_field)
        if spec is not None:
            specs.append(spec)

    chips = [chip for spec in specs for chip in _spec_chips(spec, request)]
    current_sort = next((opt for opt in sort_options if opt.selected), None)

    return FilterBar(
        search_param=search_param,
        search_value=search_value,
        specs=specs,
        ordering_param=ordering_param,
        sort_options=sort_options,
        current_sort=current_sort,
        chips=chips,
        clear_all_href=_clear_all_href(request, keep_param=ordering_param),
        target=target,
        search_placeholder=search_placeholder,
        bar_id=bar_id,
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


def _spec_chips(spec, request):
    """One removable chip per selected value; unknown/invalid values yield none."""
    label_by_value = {value: label for value, label, _checked in spec.choices}
    return [
        Chip(
            param=spec.param,
            value=value,
            label=spec.label,
            value_label=label_by_value[value],
            remove_href=_remove_value_href(request, spec.param, value),
        )
        for value in spec.selected_values
    ]


def _sort_options(bound_field):
    """
    Pair the OrderingFilter's asc/desc choices ("device" / "-device") into
    SortOptions sharing the ascending label; direction is carried as a flag so
    the template can render an icon instead of the "(descending)" suffix.
    """
    raw = bound_field.value() or []
    if isinstance(raw, str):
        raw = raw.split(",")
    current = raw[0].strip() if raw else ""

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


def _clear_all_href(request, keep_param):
    """Current URL minus all filters; ordering is presentation, not a filter."""
    query = request.GET.copy()
    for key in list(query.keys()):
        if key != keep_param:
            del query[key]
    encoded = query.urlencode()
    return f"{request.path}?{encoded}" if encoded else request.path
