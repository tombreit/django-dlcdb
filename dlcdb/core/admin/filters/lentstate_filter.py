# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.contrib.admin import SimpleListFilter
from django.db.models import Q

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
            return queryset.filter(Q(lent_desired_end_date__lte=datetime.datetime.today()) & Q(lent_end_date=None))
        elif self.value() == "lentable":
            return queryset.filter(record_type=Record.INROOM)
        elif self.value() == "lent":
            return queryset.filter(record_type=Record.LENT)
