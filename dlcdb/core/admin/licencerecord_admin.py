# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.formats import date_format

from ..models import LicenceRecord
from .base_admin import CustomBaseModelAdmin
from .filters.licence_filters import IsAssignedFilter, LicenceTypeListFilter


class LicenceRecordAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["device_note"].initial = self.instance.device.note

    device_note = forms.CharField(
        required=False,
        widget=forms.widgets.Textarea,
    )

    class Meta:
        model = LicenceRecord
        fields = "__all__"


@admin.register(LicenceRecord)
class LicenceRecordAdmin(CustomBaseModelAdmin):
    form = LicenceRecordAdminForm

    search_fields = [
        "device__sap_id",
        "device__edv_id",
        "device__manufacturer__name",
        "device__series",
        "device__serial_number",
        "person__first_name",
        "person__last_name",
        "person__email",
    ]

    list_display = [
        "get_device",
        "get_device_type",
        "get_manufacturer",
        "get_series",
        "person",
        "assigned_device",
        "get_contract_expiration_date",
        "is_assigned",
    ]

    list_filter = [
        IsAssignedFilter,
        LicenceTypeListFilter,
        # 'device__device_type',
        "person",
        "assigned_device",
    ]

    readonly_fields = [
        "get_edv_id",
        "get_sap_id",
        "get_device_ids",
        "get_device_type",
        "get_device_human_readable",
        "get_manufacturer",
        "get_series",
        "get_serial_number",
        "get_contract_expiration_date",
    ]

    autocomplete_fields = [
        "person",
        "assigned_device",
    ]

    fieldsets = (
        (
            "Device",
            {
                "fields": (
                    "get_device_ids",
                    "get_device_human_readable",
                    "get_device_type",
                    "get_serial_number",
                    "device_note",
                )
            },
        ),
        (
            "Lizenz",
            {
                "fields": (
                    (
                        "person",
                        "assigned_device",
                    ),
                    # 'room',
                    ("get_contract_expiration_date",),
                )
            },
        ),
        ("Notes", {"classes": ("collapse",), "fields": ("note",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Save related device note
        device = obj.device
        old_device_note = device.note
        new_device_note = form.cleaned_data["device_note"]

        if old_device_note != new_device_note:
            device.note = new_device_note
            device.save()
            self.log_change(
                request,
                device,
                message=f"Device note changed. Old value: `{old_device_note}` New value: `{new_device_note}`",
            )

        super().save_model(request, obj, form, change)

    def is_assigned(self, obj):
        if obj.person or obj.assigned_device:
            return True

    is_assigned.boolean = True

    def get_device(self, obj):
        return obj.device

    get_device.short_description = "Lizenz"

    def get_device_type(self, obj):
        return obj.device.device_type

    get_device_type.short_description = "Typ"

    def get_edv_id(self, obj):
        return format_html(
            '<a href="{0}" target="_blank"><strong>{1}</strong></a>',
            reverse("admin:core_device_change", args=(obj.device.pk,)),
            obj.device.edv_id,
        )

    get_edv_id.short_description = "EDV ID"

    def get_sap_id(self, obj):
        return obj.device.sap_id

    get_sap_id.short_description = "SAP ID"

    def get_device_ids(self, obj):
        return format_html(
            '<a href="{0}" target="_blank"><strong>EDV ID: <code>{1}</code> / Inventarnummer: <code>{2}</code></strong></a>',
            reverse("admin:core_device_change", args=(obj.device.pk,)),
            obj.device.edv_id,
            obj.device.sap_id,
        )

    get_device_ids.short_description = "IDs"

    def get_manufacturer(self, obj):
        return obj.device.manufacturer

    get_manufacturer.short_description = "Hersteller"

    def get_series(self, obj):
        return obj.device.series

    get_series.short_description = "Model"

    def get_serial_number(self, obj):
        return obj.device.serial_number

    get_serial_number.short_description = "Serial nr."

    def get_device_human_readable(self, obj):
        return "{} - {}".format(
            obj.device.manufacturer,
            obj.device.series,
        )

    get_device_human_readable.short_description = "Bezeichnung"

    # def get_contract_expiration_date(self, obj):
    #     return obj.device.contract_expiration_date
    # get_contract_expiration_date.short_description = 'Licence expiry date'

    def get_contract_expiration_date(self, obj):
        _title = ""
        if obj.license_state == "80-warning":
            _title = "Läuft in weniger als 60 Tagen ab!"
        elif obj.license_state == "90-danger":
            _title = "Ist schon abgelaufen!"

        return format_html(
            '<span title="{title}" class="licence-state alert-{license_state}">{contract_expiration_date}</span>',
            contract_expiration_date=date_format(obj.device.contract_expiration_date, format="DATE_FORMAT")
            if obj.device.contract_expiration_date
            else "-",
            license_state=obj.license_state,
            title=_title,
        )

    get_contract_expiration_date.short_description = "Licence expiry date"
    # get_contract_expiration_date.admin_order_field = 'obj.device.contract_expiration_date'

    class Media:
        js = ("core/licencerecord/licence.js",)
