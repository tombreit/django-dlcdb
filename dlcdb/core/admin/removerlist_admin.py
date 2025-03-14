# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..models import RemoverList
from ..forms.removerlist_admin_form import RemoverListAdminForm
from ..utils.bulk_management import set_removed_record


@admin.register(RemoverList)
class RemoverListAdmin(admin.ModelAdmin):
    form = RemoverListAdminForm

    fields = (
        "file",
        "note",
        "messages",
        "created_at",
        "modified_at",
    )

    readonly_fields = (
        "messages",
        "created_at",
        "modified_at",
    )

    list_display = [
        "get_change_link_display",
        "created_at",
        "modified_at",
        "note",
    ]

    def get_change_link_display(self, obj):
        return "{label}".format(label=obj.file)

    get_change_link_display.short_description = "CSV-Datei"

    def get_form(self, request, obj=None, **kwargs):
        """
        Add request context to form to display Django messages framework
        messages in form clean().
        """
        form = super().get_form(request, obj=obj, **kwargs)
        form.request = request
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # We only have a primary key for this object after saving
        result = set_removed_record(
            obj.file,
            username=request.user.username,
            write=True,
        )
        plaintext_messages = [
            result.removed_devices_count,
            "\n".join(result.success_messages),
        ]
        html_messages = format_html(
            "{}<br>{}<br>",
            result.removed_devices_count,
            mark_safe("<br>".join(result.success_messages)),
        )
        obj.messages = "\n".join(plaintext_messages)
        obj.save()
        messages.success(request, html_messages)
