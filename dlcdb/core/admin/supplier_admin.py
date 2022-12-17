from django.contrib import admin
from ..models import Supplier
from .base_admin import DeviceCountMixin


@admin.register(Supplier)
class SupplierAdmin(DeviceCountMixin, admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
