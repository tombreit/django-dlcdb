# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.admin import SimpleListFilter
from django.db.models import Count

from dlcdb.core import models


class DuplicateFilter(SimpleListFilter):
    title = "Dubletten"
    parameter_name = "dubletten"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """

        return (
            ("serial_number", "Seriennummern Dubletten"),
            ("nick_name", "Nickname Dubletten"),
        )

    def queryset(self, request, queryset):
        """
        Todo: make query case-insensitive
        """

        if self.value():
            duplicate_field = self.value()

            field_name = [
                # should expand to: sap_id
                duplicate_field,
            ]

            field_empty = {
                # should expand to: sap_id=''
                duplicate_field: "",
            }

            duplicates = (
                models.Device.objects.exclude(**field_empty)
                .values(*field_name)
                .annotate(count=Count("id"))
                .values(*field_name)
                .order_by()
                .filter(count__gt=1)
            )

            field_in = {
                # should expand to: sap_id__in=duplicates
                duplicate_field + "__in": duplicates,
            }

            return models.Device.objects.filter(**field_in)

        else:
            return queryset
