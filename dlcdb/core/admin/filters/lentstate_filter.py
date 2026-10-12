# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.admin import SimpleListFilter

from ...models import Record


class LentStateRecordFilter(SimpleListFilter):
    title = "Verleihstatus"
    parameter_name = "record_type"

    def lookups(self, request, model_admin):
        return (
            ("overdue", "Zur Rückgabe fällig"),
            ("lentable", "Verleihbar "),
            ("lent", "Verliehen"),
        )

    def queryset(self, request, queryset):
        if self.value() == "overdue":
            return queryset.overdue()
        elif self.value() == "lentable":
            return queryset.filter(record_type=Record.INROOM)
        elif self.value() == "lent":
            return queryset.filter(record_type=Record.LENT)
