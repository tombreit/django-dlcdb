# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import ImporterList

# An empty status marks a dry run that was previewed but never confirmed; a
# ChoiceFilter cannot select the empty string, so it gets its own value.
STATUS_NOT_CONFIRMED = "none"


class ImporterListFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter", label=_("Search"))

    status = django_filters.ChoiceFilter(
        method="status_filter",
        choices=[*ImporterList.Status.choices, (STATUS_NOT_CONFIRMED, _("Not confirmed"))],
        label=_("Status"),
        empty_label=_("Any status..."),
    )
    import_format = django_filters.ChoiceFilter(
        choices=ImporterList.ImportFormatChoices.choices,
        label=_("Format"),
        empty_label=_("Any format..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("file", "file"),
            ("devices_count", "devices"),
            ("modified_at", "modified"),
            ("created_at", "created"),
        ),
        field_labels={"created_at": _("Created")},
    )

    class Meta:
        model = ImporterList
        fields = ["search", "status", "import_format", "ordering"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(file__icontains=value) | Q(note__icontains=value))

    def status_filter(self, queryset, name, value):
        if value == STATUS_NOT_CONFIRMED:
            return queryset.filter(status="")
        return queryset.filter(status=value) if value else queryset
