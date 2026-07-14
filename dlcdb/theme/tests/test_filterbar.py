# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import django_filters
from django.test import RequestFactory, TestCase

from dlcdb.core.models import Person
from dlcdb.theme.filterbar import build_filterbar


class SampleFilter(django_filters.FilterSet):
    """
    Self-contained FilterSet covering every field kind build_filterbar
    classifies: search, single choice, model choice, multi choice, ordering.
    """

    search = django_filters.CharFilter(method="noop")
    state = django_filters.ChoiceFilter(
        choices=[("open", "Open"), ("closed", "Closed")],
        label="State",
        empty_label="Any state...",
    )
    person = django_filters.ModelChoiceFilter(
        queryset=Person.objects.all(),
        label="Person",
        empty_label="Person...",
    )
    tags = django_filters.MultipleChoiceFilter(
        choices=[("a", "Alpha"), ("b", "Beta")],
        label="Tags",
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("last_name", "name"),
            ("modified_at", "modified"),
        ),
    )

    def noop(self, queryset, name, value):
        return queryset


class BuildFilterbarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = Person.objects.create(first_name="Max", last_name="Mustermann")

    def _bar(self, query=""):
        request = RequestFactory().get(f"/items/{query}")
        # The queryset is required by FilterSet.__init__ but never touched by
        # build_filterbar; any model works.
        filterset = SampleFilter(request.GET, queryset=Person.objects.all(), request=request)
        return build_filterbar(filterset, request, target="#item-list")

    def test_classification(self):
        bar = self._bar()
        self.assertEqual(bar.search_param, "search")
        self.assertEqual(
            [(spec.param, spec.input_type, spec.multiple) for spec in bar.specs],
            [("state", "radio", False), ("person", "radio", False), ("tags", "checkbox", True)],
        )
        # 2 ordering fields x asc/desc; the empty choice is skipped.
        self.assertEqual(len(bar.sort_options), 4)
        self.assertEqual(bar.ordering_param, "ordering")

    def test_empty_label_is_first_radio_choice_and_checked_by_default(self):
        state = self._bar().specs[0]
        self.assertEqual(state.choices[0], ("", "Any state...", True))
        self.assertTrue(all(not checked for value, label, checked in state.choices[1:]))

    def test_selected_choice_is_checked_instead_of_reset(self):
        state = self._bar("?state=open").specs[0]
        checked_values = [value for value, label, checked in state.choices if checked]
        self.assertEqual(checked_values, ["open"])

    def test_selected_labels(self):
        bar = self._bar(f"?state=open&person={self.person.pk}&tags=a&tags=b")
        state, person, tags = bar.specs
        self.assertEqual(state.selected_label, "Open")
        self.assertEqual(person.selected_label, str(self.person))
        self.assertEqual(tags.selected_values, ["a", "b"])
        self.assertEqual(tags.selected_label, "2 selected")

    def test_chips_remove_exactly_one_value(self):
        bar = self._bar(f"?state=open&person={self.person.pk}&tags=a&tags=b&ordering=-modified")
        self.assertEqual(len(bar.chips), 4)

        state_chip = next(chip for chip in bar.chips if chip.param == "state")
        self.assertEqual(state_chip.value_label, "Open")
        self.assertNotIn("state=", state_chip.remove_href)
        self.assertIn(f"person={self.person.pk}", state_chip.remove_href)
        self.assertIn("ordering=-modified", state_chip.remove_href)

        # Removing one multiselect value keeps the sibling value.
        tag_a_chip = next(chip for chip in bar.chips if chip.param == "tags" and chip.value == "a")
        self.assertNotIn("tags=a", tag_a_chip.remove_href)
        self.assertIn("tags=b", tag_a_chip.remove_href)

    def test_search_chip(self):
        bar = self._bar("?search=laptop")
        self.assertIsNotNone(bar.search_chip)
        self.assertEqual(bar.search_chip.param, "search")
        self.assertEqual(bar.search_chip.value_label, "laptop")
        self.assertNotIn("search=", bar.search_chip.remove_href)
        # The search chip is separate from the dropdown-filter chips.
        self.assertEqual(bar.chips, [])

    def test_no_search_chip_without_query(self):
        self.assertIsNone(self._bar("?state=open").search_chip)

    def test_clear_all_keeps_only_ordering(self):
        bar = self._bar("?search=laptop&state=open&tags=a&ordering=-modified")
        self.assertEqual(bar.clear_all_href, "/items/?ordering=-modified")

    def test_clear_all_without_ordering_is_bare_path(self):
        bar = self._bar("?state=open")
        self.assertEqual(bar.clear_all_href, "/items/")

    def test_invalid_value_yields_no_chip_and_no_crash(self):
        bar = self._bar("?state=bogus&person=999999")
        self.assertEqual(bar.chips, [])
        self.assertEqual(bar.specs[0].selected_label, "")

    def test_current_sort(self):
        bar = self._bar("?ordering=-modified")
        self.assertIsNotNone(bar.current_sort)
        self.assertEqual(bar.current_sort.value, "-modified")
        self.assertEqual(bar.current_sort.label, "Modified")
        self.assertTrue(bar.current_sort.descending)
        self.assertEqual(sum(opt.selected for opt in bar.sort_options), 1)

    def test_no_ordering_selected_without_param(self):
        bar = self._bar("?state=open")
        self.assertIsNone(bar.current_sort)

    def test_default_secondary_fields_is_empty_and_unchanged_behavior(self):
        bar = self._bar()
        self.assertEqual(bar.secondary_specs, [])
        self.assertFalse(bar.secondary_active)

    def test_secondary_fields_are_routed_out_of_specs(self):
        request = RequestFactory().get("/items/")
        filterset = SampleFilter(request.GET, queryset=Person.objects.all(), request=request)
        bar = build_filterbar(filterset, request, target="#item-list", secondary_fields={"tags"})

        self.assertEqual([spec.param for spec in bar.specs], ["state", "person"])
        self.assertEqual([spec.param for spec in bar.secondary_specs], ["tags"])

    def test_secondary_active_true_only_when_a_secondary_filter_is_selected(self):
        request = RequestFactory().get("/items/?state=open")
        filterset = SampleFilter(request.GET, queryset=Person.objects.all(), request=request)
        bar = build_filterbar(filterset, request, target="#item-list", secondary_fields={"tags"})
        self.assertFalse(bar.secondary_active)

        request = RequestFactory().get("/items/?tags=a")
        filterset = SampleFilter(request.GET, queryset=Person.objects.all(), request=request)
        bar = build_filterbar(filterset, request, target="#item-list", secondary_fields={"tags"})
        self.assertTrue(bar.secondary_active)

    def test_secondary_filter_value_still_produces_a_chip(self):
        request = RequestFactory().get("/items/?tags=a")
        filterset = SampleFilter(request.GET, queryset=Person.objects.all(), request=request)
        bar = build_filterbar(filterset, request, target="#item-list", secondary_fields={"tags"})

        self.assertEqual(len(bar.chips), 1)
        self.assertEqual(bar.chips[0].param, "tags")
