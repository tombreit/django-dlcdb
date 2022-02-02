from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from ..models import Attachment, Device
from .base_admin import CustomBaseModelAdmin


class AttachmentAdmin(CustomBaseModelAdmin):

    fields = (
        'title',
        'file',
        'get_records',
        'user',
        'username',
        'created_at',
        'modified_at',
    )

    readonly_fields = (
        'username',
        'user',
        'get_records',
        'created_at',
        'modified_at',
    )

    list_display = (
        'title',
        'file',
        'created_at',
        'get_records',
    )

    search_fields = [
        'title',
        'file',
    ]

    def get_records(self, obj):
        # records = obj.record_set.all().values_list('pk', flat=True)
        # qs = Device.objects.filter(active_record__pk__in=records)
        related_records = obj.record_set.all()
        if related_records:
            record_links = []
            for record in related_records:
                record_url = reverse('admin:core_record_change', args=(record.pk,))
                record_links.append(
                    f"<a href='{record_url}'>{record} / {record.record_type} / {record.created_at:%Y-%m-%d}</a><br>"
                )

            return format_html("".join(record_links))

admin.site.register(Attachment, AttachmentAdmin)
