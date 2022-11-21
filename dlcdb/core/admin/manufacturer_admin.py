from django.db.models import Count
from django.contrib import admin
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import format_html

from ..models import Manufacturer


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_assets_count']
    search_fields = ['name', 'note']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _assets_count=Count("device", distinct=True),
        )
        return queryset

    @admin.display(
        description='Assets',
        ordering='-_assets_count',
    )
    def get_assets_count(self, obj):
        return format_html(
            '<a href="{url}?{query_kwargs}"><b>{count}</b></a>',
            url=reverse('admin:core_device_changelist'),
            query_kwargs=urlencode({'manufacturer__id__exact': obj.pk}),
            count=obj._assets_count,
        )
