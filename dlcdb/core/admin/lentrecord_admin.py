# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import datetime

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.forms import ValidationError
from django.http import HttpResponseRedirect
from django.db.models import Case, CharField, Value, When
from django.utils.formats import date_format
from django.contrib import messages

from dlcdb.tenants.admin import TenantScopedAdmin
from dlcdb.lending.models import LendingConfiguration
from ..models import LentRecord, InRoomRecord, Room, Record
from ..forms.lentrecordadmin_form import LentRecordAdminForm
from ..utils.helpers import get_denormalized_user
from .filters.lentstate_filter import LentStateRecordFilter
from .base_admin import CustomBaseModelAdmin, ExportCsvMixin

# Create a session store to pass the new created instance.pk from save_model()
# to response_change(). Considered a dirty hack.
# Ref: https://docs.djangoproject.com/en/dev/topics/http/sessions/#using-sessions-out-of-views
#
# Todo: refactor, get rid of session store and handle the redirect in a
# friendlier way.
from importlib import import_module
from django.conf import settings

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
session = SessionStore()


@admin.register(LentRecord)
class LentRecordAdmin(TenantScopedAdmin, ExportCsvMixin, CustomBaseModelAdmin):
    form = LentRecordAdminForm
    change_form_template = "core/lentrecord/change_form.html"
    change_list_template = "core/lentrecord/change_list.html"

    search_fields = [
        "device__sap_id",
        "device__edv_id",
        "device__uuid",
        "device__manufacturer__name",
        "device__series",
        "person__first_name",
        "person__last_name",
        "person__email",
        "lent_accessories",
        "lent_note",
    ]

    list_display = [
        "get_device",
        "get_manufacturer",
        "get_series",
        "get_is_currently_lented",
        "room",
        "person",
        "lent_start_date",
        # 'lent_desired_end_date',
        "get_lent_desired_end_date",
    ]

    list_filter = [
        LentStateRecordFilter,
        "device__device_type",
        "person",
    ]

    actions = [
        "export_as_csv",
    ]

    readonly_fields = [
        "get_edv_id",
        "get_sap_id",
        "get_device_ids",
        "get_device_human_readable",
        "get_manufacturer",
        "get_series",
        "get_tenant",
    ]

    autocomplete_fields = [
        "person",
        "room",
    ]

    fieldsets = (
        (
            "Device",
            {
                "fields": (
                    "get_device_ids",
                    ("get_device_human_readable", "get_tenant"),
                )
            },
        ),
        (
            "Ausleihe",
            {
                "fields": (
                    (
                        "person",
                        "room",
                    ),
                    (
                        "lent_start_date",
                        "lent_desired_end_date",
                    ),
                )
            },
        ),
        ("Rückgabe", {"fields": ("lent_end_date",)}),
        (
            "Notes",
            {
                "classes": ("collapse",),
                "fields": (
                    "lent_accessories",
                    "lent_note",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        lending_configuration = LendingConfiguration.load()
        admin_mark_overdue = lending_configuration.admin_mark_overdue

        # see: https://docs.djangoproject.com/en/3.0/ref/models/conditional-expressions/#django.db.models.expressions.Case
        when_clauses = []
        if admin_mark_overdue:
            when_clauses.append(When(lent_desired_end_date__lte=datetime.today().date(), then=Value("20-overdue")))

        when_clauses.extend(
            [
                When(record_type=Record.INROOM, then=Value("30-available")),
                When(record_type=Record.LENT, then=Value("40-lent")),
            ]
        )

        queryset = queryset.annotate(
            lent_state=Case(
                *when_clauses,
                default=Value("10-unknown"),
                output_field=CharField(),
            )
        ).order_by("lent_state")

        return queryset

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Verleihgerät")
    @admin.display(ordering="device__edv_id")
    def get_device(self, obj):
        return format_html(
            '<a href="{0}"><strong>{1}</strong></a>',
            reverse("admin:core_lentrecord_change", args=(obj.pk,)),
            obj.device,
        )

    @admin.display(description="EDV ID")
    def get_edv_id(self, obj):
        return format_html(
            '<a href="{0}" target="_blank"><strong>{1}</strong></a>',
            reverse("admin:core_device_change", args=(obj.device.pk,)),
            obj.device.edv_id,
        )

    @admin.display(description="SAP ID")
    def get_sap_id(self, obj):
        return obj.device.sap_id

    @admin.display(description="IDs")
    def get_device_ids(self, obj):
        return format_html(
            '<a href="{0}" target="_blank"><strong>EDV ID: <code>{1}</code> / Inventarnummer: <code>{2}</code></strong></a>',
            reverse("admin:core_device_change", args=(obj.device.pk,)),
            obj.device.edv_id,
            obj.device.sap_id,
        )

    @admin.display(description="Hersteller")
    @admin.display(ordering="device__manufacturer")
    def get_manufacturer(self, obj):
        return obj.device.manufacturer

    @admin.display(description="Model")
    @admin.display(ordering="device__series")
    def get_series(self, obj):
        return obj.device.series

    @admin.display(description="Tenant")
    def get_tenant(self, obj):
        return obj.device.tenant

    @admin.display(description="Soll-Rückgabedatum")
    @admin.display(ordering="lent_desired_end_date")
    def get_lent_desired_end_date(self, obj):
        return format_html(
            '<span class="lent-state lent-state-{lent_state}">{lent_desired_end_date}</span>',
            lent_desired_end_date=date_format(obj.lent_desired_end_date, format="DATE_FORMAT")
            if obj.lent_desired_end_date
            else "-",
            lent_state=obj.lent_state,
        )

    @admin.display(description="Bezeichnung")
    def get_device_human_readable(self, obj):
        return "{} - {}".format(
            obj.device.manufacturer,
            obj.device.series,
        )

    @admin.display(description="Verliehen")
    @admin.display(boolean=True)
    def get_is_currently_lented(self, obj):
        return obj.is_type_lent

    def get_form(self, request, obj=None, **kwargs):
        """
        Pass current record_type of device to form for validation.
        """
        form = super().get_form(request, obj=obj, **kwargs)
        form.record_type = obj.record_type
        return form

    def save_model(self, request, obj, form, change):
        """
        By saving a record, check original record type and create new records
        if neccessary.
        """

        # Soft warnings
        desired_lent_end_date = obj.lent_desired_end_date
        contract_end_date = obj.person.udb_contract_planned_checkout

        if not contract_end_date:
            messages.warning(request, f"Warnung: Kein UDB Vertragsablaufdatum für {obj.person} gefunden!")

        if contract_end_date:
            if desired_lent_end_date >= contract_end_date:
                messages.warning(request, "Warnung: Vertragsende vor Soll-Rückgabedatum!")

        # Save logic
        user, username = get_denormalized_user(request.user)

        if obj.record_type == Record.LENT and obj.lent_end_date and obj.active_device_record:
            # War ein LENT record und hat jetzt einen Rückgabe-Timestamp,
            # muss gespeichert werden und ein neuer INROOM record angelegt werden:
            # print("Trigger returning of item, setting new InRoomRecord...")
            super().save_model(request, obj, form, change)

            instance = InRoomRecord(
                device=obj.device,
                room=Room.objects.get(is_auto_return_room=True),
                user=user,
                username=username,
            )
            instance.save()

        elif obj.record_type == Record.LENT:
            # War schon ein LENT record, wird lediglich geändert:
            # print(f"Already a LENT record, possibly changed. record pk: {obj.pk}.")
            super().save_model(request, obj, form, change)
            # Force redirect to this pk to avoid redirects to a pk stored in a
            # previous session:
            session["new_instance_pk"] = None

        elif obj.record_type == Record.INROOM:
            # War ein INROOM record, muss als neuer LENT record gespeichert werden:
            # print("Trigger lent action: was INROOM record...")

            instance = LentRecord(
                device=obj.device,
                room=obj.room if obj.room else 0,
                user=user,
                username=username,
                # Lent specific fields:
                person=obj.person,
                lent_start_date=obj.lent_start_date,
                lent_desired_end_date=obj.lent_desired_end_date,
                lent_note=obj.lent_note,
                lent_reason=obj.lent_reason,
                lent_accessories=obj.lent_accessories,
            )
            instance.save()
            session["new_instance_pk"] = instance.pk

        else:
            raise ValidationError("Lent state unknown - please report this issue!")

    def response_change(self, request, obj):
        is_new_lending_action = bool(session.get("new_instance_pk"))
        is_return_action = bool(obj.lent_end_date)

        if is_return_action:
            msg = f"Verleih von “{self.get_device_human_readable(obj)}” an “{obj.person}” beendet."
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)
        elif is_new_lending_action:
            msg = f"Verleih von “{self.get_device_human_readable(obj)}” für “{obj.person}” hinzugefügt."
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse("admin:core_lentrecord_change", args=(session["new_instance_pk"],))
            return HttpResponseRedirect(redirect_url)
        else:
            msg = f"Verleih von “{self.get_device_human_readable(obj)}” an “{obj.person}” gespeichert."
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            return HttpResponseRedirect(redirect_url)

    def response_post_save_change(self, request, obj):
        """
        Figure out where to redirect after the 'Save' button has been pressed
        when editing an existing object.
        """
        return self._response_post_save(request, obj)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context.update(
            {
                "show_save": False,
            }
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

    class Media:
        js = ("core/lentrecord/lent.js",)
