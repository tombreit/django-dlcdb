from django.contrib import admin
from django.db import models
from django.forms import Textarea

from .models import Thing, AssignedThing


@admin.register(AssignedThing)
class AssignedThingAdmin(admin.ModelAdmin):

    list_display = [
        'thing',
        'person',
        'assigned_at',
        'assigned_by',
        'unassigned_at',
        'unassigned_by'
    ]

    list_filter = [
        'person',
        'thing',
        'assigned_at',
        'unassigned_at',
    ]

    search_fields = [
        'person__last_name',
        'person__first_name',
        'thing__name',
        'thing__slug',
    ]

    autocomplete_fields = [
        'person',
        'thing',
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Thing)
class ThingAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'slug',
    ]
