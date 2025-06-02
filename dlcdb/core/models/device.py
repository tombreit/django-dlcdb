# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import models
from django.db.models import Case, When, F, Value, CharField
from django.db.models.functions import Concat, Cast, Coalesce, Trim
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.contrib.sites.models import Site

from simple_history.models import HistoricalRecords

from dlcdb.inventory.utils import uuid2qrcode
from dlcdb.tenants.models import TenantAwareModel

from ..utils.device_methods import get_device_state_data
from ..storage import OverwriteStorage
from .abstracts import SoftDeleteAuditBaseModel
from .supplier import Supplier


class DeviceManager(models.Manager):
    def get_queryset(self):
        base_qs = super().get_queryset()

        annotated_qs = base_qs.annotate(
            human_title=Case(
                When(
                    (models.Q(manufacturer__name__isnull=False) & ~models.Q(manufacturer__name__exact=""))
                    | (models.Q(supplier__name__isnull=False) & ~models.Q(supplier__name__exact=""))
                    | (models.Q(series__isnull=False) & ~models.Q(series__exact="")),
                    then=Trim(
                        Concat(
                            Coalesce(F("manufacturer__name"), F("supplier__name"), Value("")),
                            Value(" "),
                            Case(
                                When(series__isnull=False, series__gt="", then=F("series")),
                                default=Value(""),
                                output_field=CharField(),
                            ),
                            Case(
                                When(
                                    sap_id__isnull=False,
                                    sap_id__gt="",
                                    then=Concat(Value(" ("), F("sap_id"), Value(")")),
                                ),
                                default=Value(""),
                                output_field=CharField(),
                            ),
                            output_field=CharField(),
                        )
                    ),
                ),
                default=Cast("uuid", output_field=CharField()),
                output_field=CharField(),
            )
        )

        return annotated_qs


class Device(TenantAwareModel, SoftDeleteAuditBaseModel):
    objects = DeviceManager()

    active_record = models.OneToOneField(
        "Record",
        on_delete=models.CASCADE,
        related_name="active_device_record",
        blank=True,
        null=True,
        db_index=True,
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    # We're keeping null=True for edv_id and sap_id to ensure uniqueness
    # checks on db level, as empty strings ('') are considered equal
    edv_id = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_("IT ID"),
    )

    sap_id_validator = RegexValidator(
        regex="^[0-9]+-[0-9]+$",
        message=_("Inventory number must be entered as the main number-sub-number."),
        code="invalid_sap_id",
    )

    sap_id = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_("Inventory ID"),
        help_text="SAP-Nummer. Format: `Hauptnummer-Unternummer`. Für Anlagen die ausschließlich eine Hauptnummer besitzen, ist die 0 (Null) als Unternummer einzutragen.",
        validators=[sap_id_validator],
    )
    serial_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Serial number"),
    )
    device_type = models.ForeignKey(
        "core.DeviceType",
        null=True,
        blank=True,
        verbose_name=_("Device type"),
        on_delete=models.PROTECT,
        limit_choices_to={"deleted_at__isnull": True},
    )
    manufacturer = models.ForeignKey(
        "core.Manufacturer",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_("Manufacturer"),
    )
    series = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Model name"),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True, verbose_name=_("Supplier"))
    is_licence = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is license?"),
    )
    purchase_date = models.DateField(null=True, blank=True, verbose_name=_("Date of purchase"))
    warranty_expiration_date = models.DateField(null=True, blank=True, verbose_name=_("Warranty expiry date"))
    contract_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Start date of licence or maintenance contract")
    )
    contract_expiration_date = models.DateField(
        null=True, blank=True, verbose_name=_("Expiry date licence or maintenance contract")
    )
    contract_termination_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Contract termination date"),
        help_text=_("Date of termination of the contract."),
    )
    cost_centre = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Cost centre"))
    book_value = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Book value"))
    procurement_note = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Procurement note"),
        help_text=_("Information such as unique selling points, possible suppliers for comparative offers, etc."),
    )

    contact_person_internal = models.ForeignKey(
        "core.Person",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="device_contact_internal",
        verbose_name=_("Contact (internal)"),
    )

    note = models.TextField(null=True, blank=True, verbose_name=_("Note"))
    mac_address = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Main MAC address"))
    extra_mac_addresses = models.TextField(null=True, blank=True, verbose_name=_("Further MAC addresses"))
    nick_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Nickname / C-Name"))
    is_legacy = models.BooleanField(default=False, verbose_name=_("Legacy device"))

    is_lentable = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is loanable?"),
    )
    is_imported = models.BooleanField(default=False, verbose_name=_("Added via CSV import?"))
    imported_by = models.ForeignKey(
        "core.ImporterList",
        null=True,
        blank=True,
        verbose_name="Importiert via",
        on_delete=models.SET_NULL,
    )
    qrcode = models.FileField(
        upload_to=f"{settings.QRCODE_DIR}/",
        blank=True,
        null=True,
        storage=OverwriteStorage(),
    )
    order_number = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Order number"),
    )
    machine_encryption_key = models.TextField(
        blank=True,
        verbose_name=_("Password Hard Disk Encryption"),
        help_text=_("E.g. Bitlocker recovery key or macOS FileVault password for system hard disk."),
    )
    backup_encryption_key = models.TextField(
        blank=True,
        verbose_name=_("Password backup encryption"),
        help_text=_("E.g. macOS TimeMachine password for backup hard disk."),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Device"
        verbose_name_plural = "Devices"
        ordering = ["-modified_at", "edv_id"]
        indexes = [
            models.Index(fields=["edv_id", "sap_id", "modified_at"]),
        ]

    def __repr__(self):
        return str(self.uuid)

    def __str__(self):
        return self.edv_id or self.sap_id or str(self.uuid)

    def save(self, *args, **kwargs):
        if not self.qrcode:
            qrcode = uuid2qrcode(self.uuid, infix=settings.QRCODE_INFIXES.get("device"))
            self.qrcode.save(qrcode.filename, qrcode.fileobj, save=False)
        super().save(*args, **kwargs)

    def get_latest_note(self):
        """
        Returns the latest note for this device and the current inventory.
        """
        return self.device_notes.filter(inventory__is_active=True).order_by("-created_at").first()

    def has_record_notes(self):
        return self.record_set.exclude(note__isnull=True).exclude(note__exact="").exists()

    @property
    def get_is_currently_lented(self):
        if not self.active_record:
            return False
        else:
            return all(
                [
                    self.active_record.is_type_lent,
                    self.active_record.lent_end_date is None,
                ]
            )

    @property
    def get_lent_start_date(self):
        return self.active_record.lent_start_date

    @property
    def get_lent_desired_end_date(self):
        return self.active_record.lent_desired_end_date

    @property
    def get_lent_end_date(self):
        return self.active_record.lent_end_date

    @property
    def get_person(self):
        return self.active_record.person

    @property
    def get_lent_note(self):
        return self.active_record.lent_note

    @property
    def get_room(self):
        return self.active_record.room

    @property
    def get_current_inventory_records(self):
        """
        Try to get the latest record which has an inventory stamp attached.
        """
        from ..models import Inventory, Record

        try:
            current_inventory = Inventory.objects.get(is_active=True)
            already_inventorized = self.record_set.order_by("pk").filter(
                inventory=current_inventory,
            )

            # Did not use qs.last() convenience method as I want to
            # catch an exception for no matching record found.
            # already_inventorized = already_inventorized[:1].get()

            # We are more flexibble if returning the queryset with matched
            # inventorized records.

        except Inventory.DoesNotExist:
            already_inventorized = None
        except Record.DoesNotExist:
            already_inventorized = None
        except Exception as e:
            raise Exception(f"Exception: {e=}")

        return already_inventorized

    def get_timeline(self):
        """
        Returns the license timelicense.get_license_state_labelline as a list of tuples.
        """
        timeline = []

        added_date = self.created_at.date()
        start_date = self.contract_start_date
        end_date = self.contract_expiration_date
        today = timezone.now().date()

        # Return early
        if not start_date or not end_date:
            return timeline

        total_days = (end_date - added_date).days
        if total_days <= 0:
            return timeline

        @dataclass
        class TimelineEvent:
            event_type: str
            percentage: int
            date: object  # date object
            description: str
            bg: str = "#ff0000"

        # Calculate durations between events and convert to percentages
        events = [
            (added_date, "added", "Added", "#ff0000"),
            (start_date, "start", "Start date", "#00ff00"),
            (today, "today", "Today", "#ff0000"),
            (end_date, "end", "Expiry date", "#ff0000"),
        ]
        events.sort()  # Sort events chronologically

        # Calculate percentages based on duration between events
        running_percentage = 0
        for i in range(len(events) - 1):
            current_date, event_type, description, bg = events[i]
            duration = (events[i + 1][0] - current_date).days
            percentage = int((duration / total_days) * 100)

            timeline.append(
                TimelineEvent(
                    event_type=event_type, percentage=percentage, date=current_date, description=description, bg=bg
                )
            )
            running_percentage += percentage

        # Add final event
        timeline.append(
            TimelineEvent(
                event_type=events[-1][1],
                percentage=int(100 - running_percentage),
                date=events[-1][0],
                description=events[-1][2],
                bg=events[-1][3],
            )
        )

        if self.contract_termination_date:
            timeline.append(
                TimelineEvent(
                    event_type="termination",
                    percentage=int(((self.contract_termination_date - added_date).days / total_days) * 100),
                    date=self.contract_termination_date,
                    description="Termination date",
                )
            )

        # Sort timeline events by percentage chronologically
        timeline.sort(key=lambda x: x.date)
        return timeline

    # @property
    # def get_subscribers(self):
    #     # Todo: Refactor to use a annotated queryset or load this via HTMX
    #     subscriber_ids = self.subscription_set.all().values_list("subscriber", flat=True)
    #     subscribers_emails = (
    #         Person.objects.filter(id__in=subscriber_ids).exclude(email__isnull=True).exclude(email="")
    #     ).values_list("email", flat=True)

    #     return subscribers_emails

    def get_edv_id(self):
        return self.edv_id or "----"

    get_edv_id.short_description = "EDV ID"

    def get_absolute_url(self):
        if self.is_licence:
            absolute_url = reverse("licenses:edit", kwargs={"license_id": self.pk})
            return absolute_url

    def get_fqdn_url(self):
        if self.get_absolute_url():
            return f"https://{Site.objects.get_current().domain}{self.get_absolute_url()}"
        return None

    def get_state_data(self, *, user=None, app_name=None):
        return get_device_state_data(self, user=user, app_name=app_name)
