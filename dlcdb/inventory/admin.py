# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.template import Template, Context
from django.urls import reverse
from .models import SapList, SapListComparisonResult


@admin.register(SapList)
class SapListAdmin(admin.ModelAdmin):
    list_display = [
        "get_change_link_display",
        "created_at",
        "get_compare_button_display",
        "note",
    ]

    def get_change_link_display(self, obj):
        return "{label} öffnen".format(label=obj.get_file_name())

    get_change_link_display.short_description = "Datei"

    def get_compare_button_display(self, obj):
        return Template(
            '<div class="bt"><a class="btn btn-primary" href="{{url}}"><i class="fa fa-angle-right"></i> Abgleichen</a></div>'
        ).render(Context(dict(url=reverse("inventory:compare-sap-list", kwargs=dict(pk=obj.id)))))

    get_compare_button_display.short_description = "Abgleich"


# TODO: remove this admin after refactoring
@admin.register(SapListComparisonResult)
class SapListComparisonResultAdmin(admin.ModelAdmin):
    pass
