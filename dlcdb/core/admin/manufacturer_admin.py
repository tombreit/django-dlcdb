from django.contrib import admin

from ..models import Manufacturer
from .base_admin import DeviceCountMixin


@admin.register(Manufacturer)
class ManufacturerAdmin(DeviceCountMixin, admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name', 'note']
