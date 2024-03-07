# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.template import Template, Context
from django.urls import reverse

from ..models import OrderedRecord
from .base_admin import NoModificationModelAdminMixin
from .record_admin import CustomRecordModelAdmin


@admin.register(OrderedRecord)
class OrderedRecordAdmin(NoModificationModelAdminMixin, CustomRecordModelAdmin):
    change_form_template = "core/record/change_form.html"
    list_display = ["get_device_link", "date_of_purchase"]
    fields = ["device"]

    def get_device_link(self, obj):
        return Template('<a href="{{url}}">{{label}}</a>').render(
            Context(dict(url=reverse("admin:core_device_change", args=[obj.device.id]), label=obj.device))
        )

    get_device_link.short_description = "Gerät"
