# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import admin, messages
from django.db.models import Case, CharField, Value, When
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from dlcdb.dataexchange.admin import ExportCsvMixin
from dlcdb.lending.models import LendingConfiguration
from dlcdb.tenants.admin import TenantScopedRecordAdmin

from ..forms.lentrecordadmin_form import LentRecordAdminForm
from ..models import LentRecord, Record
from ..utils.links import linked_message, obj_link
from .base_admin import CustomBaseModelAdmin
from .filters.lentstate_filter import LentStateRecordFilter


@admin.register(LentRecord)
class LentRecordAdmin(TenantScopedRecordAdmin, ExportCsvMixin, CustomBaseModelAdmin):
    form = LentRecordAdminForm
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
            _("Device"),
            {
                "fields": (
                    "get_device_ids",
                    ("get_device_human_readable", "get_tenant"),
                )
            },
        ),
        (
            _("Lending"),
            {
                "fields": (
                    (
                        "person",
                        "room",
                    ),
                    (
                        "lent_start_date",
                        "lent_desired_end_date",
                        "sync_lent_end_date",
                    ),
                )
            },
        ),
        (_("Return"), {"fields": ("lent_end_date",)}),
        (
            _("Notes"),
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
            when_clauses.append(When(LentRecord.overdue_q(), then=Value("20-overdue")))

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

    @admin.display(description=_("Lent device"))
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

    @admin.display(description=_("Manufacturer"))
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

    @admin.display(description=_("Desired return date"))
    @admin.display(ordering="lent_desired_end_date")
    def get_lent_desired_end_date(self, obj):
        return format_html(
            '<span class="lent-state lent-state-{lent_state}">{lent_desired_end_date}</span>',
            lent_desired_end_date=date_format(obj.lent_desired_end_date, format="DATE_FORMAT")
            if obj.lent_desired_end_date
            else "-",
            lent_state=obj.lent_state,
        )

    @admin.display(description=_("Description"))
    def get_device_human_readable(self, obj):
        return f"{obj.device.manufacturer} - {obj.device.series}"

    @admin.display(description=_("Lent"))
    @admin.display(boolean=True)
    def get_is_currently_lented(self, obj):
        return obj.is_type_lent

    def save_model(self, request, obj, form, change):
        """
        Shows the HR contract warnings and saves through the lend, return and edit
        dispatch the lending frontend uses too (``LentRecord.contract_warnings``,
        ``LentRecord.apply_lending``).

        After a lend, ``response_change()`` redirects to the new lending. It runs in
        the same request, so the request carries it; nothing outlives the request.
        """
        for warning in obj.contract_warnings():
            messages.warning(request, warning)

        lending = obj.apply_lending(user=request.user)
        if obj.record_type == Record.INROOM:
            request.new_lending = lending

    def response_change(self, request, obj):
        new_lending = getattr(request, "new_lending", None)
        is_return_action = bool(obj.lent_end_date)

        # Keep the "manufacturer - series" wording this admin has always used for
        # the device, but make it a link to the device detail.
        device_link = obj_link(obj.device, label=self.get_device_human_readable(obj))

        if is_return_action:
            msg = linked_message(
                _("Return of “{device}” from “{person}” acknowledged."),
                device=device_link,
                person=obj.person,
            )
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)
        elif new_lending is not None:
            msg = linked_message(
                _("Device “{device}” lent to “{person}”."),
                device=device_link,
                person=obj.person,
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse("admin:core_lentrecord_change", args=(new_lending.pk,))
            return HttpResponseRedirect(redirect_url)
        else:
            msg = linked_message(
                _("Lending of “{device}” to “{person}” saved."),
                device=device_link,
                person=obj.person,
            )
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
