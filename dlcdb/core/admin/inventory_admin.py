from django.contrib import admin

from ..models import Record, Inventory


# class RecordInline(admin.TabularInline):
#     model = Record
#     fields = ['record_type', 'device', 'person', 'room']
#     readonly_fields = ['record_type', 'device', 'person', 'room']

#     def get_queryset(self, request):
#         return super().get_queryset(request).filter(is_active=True)


class InventoryAdmin(admin.ModelAdmin):
    model = Inventory
    list_display = ['name', 'is_active']
    # inlines = [
    #     RecordInline,
    # ]

admin.site.register(Inventory, InventoryAdmin)