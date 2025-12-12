# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from ..models import Attachment, Link
from .base_admin import CustomBaseModelAdmin


@admin.register(Attachment)
class AttachmentAdmin(CustomBaseModelAdmin):
    fields = (
        "title",
        "file",
        "get_records",
        "user",
        "username",
        "created_at",
        "modified_at",
    )

    readonly_fields = (
        "username",
        "user",
        "get_records",
        "created_at",
        "modified_at",
    )

    list_display = (
        "title",
        "file",
        "created_at",
        "get_records",
    )

    search_fields = [
        "title",
        "file",
    ]

    def get_records(self, obj):
        # records = obj.record_set.all().values_list('pk', flat=True)
        # qs = Device.objects.filter(active_record__pk__in=records)
        related_records = obj.record_set.all()
        if related_records:
            record_links = []
            for record in related_records:
                record_url = reverse("admin:core_record_change", args=(record.pk,))
                record_links.append(
                    f"<a href='{record_url}'>{record} / {record.record_type} / {record.created_at:%Y-%m-%d}</a><br>"
                )

            return format_html("".join(record_links))


@admin.register(Link)
class LinkAdmin(CustomBaseModelAdmin):
    list_display = [
        "linktext",
        "has_file",
        "has_url",
    ]
    search_fields = [
        "name",
    ]

    @admin.display(description="Has File?", boolean=True)
    def has_file(self, obj):
        return bool(obj.file)

    @admin.display(description="Has URL?", boolean=True)
    def has_url(self, obj):
        return bool(obj.url)

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_permission(self, request, obj=None):
        return request.user.is_superuser
