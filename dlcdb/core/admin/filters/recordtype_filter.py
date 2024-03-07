# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.admin import SimpleListFilter


class HasRecordFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = "Hat einen record?"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "has_record"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ("has_record", "Ja"),
            ("has_no_record", "Nein"),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == "has_record":
            return queryset.filter(record__isnull=False)

        if self.value() == "has_no_record":
            return queryset.filter(record__isnull=True)
