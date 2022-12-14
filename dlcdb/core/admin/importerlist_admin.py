import re

from django.contrib import admin
from django.contrib import messages

from ..models import ImporterList


@admin.register(ImporterList)
class ImporterListAdmin(admin.ModelAdmin):

    fields = (
        'file',
        'note',
        'messages',
        'created_at',
        'modified_at',
    )

    readonly_fields = (
        'messages',
        'created_at',
        'modified_at',
    )

    list_display = [
        'get_change_link_display',
        'created_at',
        'modified_at',
        'note',
    ]

    def get_change_link_display(self, obj):
        return '{label}'.format(label=obj.file)
    get_change_link_display.short_description = 'CSV-Datei'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # message_match = re.search('Imported devices\:\s(\d*)', obj.messages)
        # admin_success_msg = "{} devices imported. See 'message' field for further information.".format(message_match.group(1))
        # messages.add_message(request, messages.INFO, admin_success_msg)
