# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters used by the users list."""

import django_filters
from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


class UserFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="search_filter", label=_("Search"))
    status = django_filters.ChoiceFilter(
        label=_("Status"),
        choices=[("active", _("Active")), ("deactivated", _("Deactivated"))],
        method="status_filter",
        empty_label=_("Any status..."),
    )
    group = django_filters.ModelChoiceFilter(
        label=_("Group"),
        queryset=Group.objects.order_by("name"),
        field_name="groups",
        empty_label=_("Any group..."),
    )
    ordering = django_filters.OrderingFilter(
        fields=(("email", "email"), ("last_login", "last_login")),
        field_labels={"email": _("Email"), "last_login": _("Last login")},
    )

    class Meta:
        model = CustomUser
        fields = ["search", "status", "group", "ordering"]

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(email__icontains=value) | Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )

    def status_filter(self, queryset, name, value):
        return queryset.filter(is_active=value == "active")
