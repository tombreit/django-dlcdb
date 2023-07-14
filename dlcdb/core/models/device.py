import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from simple_history.models import HistoricalRecords

from dlcdb.inventory.utils import uuid2qrcode
from dlcdb.tenants.models import TenantAwareModel

from ..storage import OverwriteStorage
from .abstracts import SoftDeleteAuditBaseModel
from .supplier import Supplier


class Device(TenantAwareModel, SoftDeleteAuditBaseModel):
    """
    Represents a single Device. There are tons of device types.
    """

    active_record = models.OneToOneField(
        'Record',
        on_delete=models.CASCADE,
        related_name='active_device_record',
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
        verbose_name='EDV-Nummer',
    )

    sap_id_validator =  RegexValidator(
        regex='^[0-9]+-[0-9]+$',
        message='Inventarnummer muss als Hauptnummer-Unternummer eingegeben werden.',
        code='invalid_sap_id'
    )

    sap_id = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_('Inventory ID'),
        help_text='SAP-Nummer. Format: `Hauptnummer-Unternummer`. Für Anlagen die ausschließlich eine Hauptnummer besitzen, ist die 0 (Null) als Unternummer einzutragen.',
        validators=[sap_id_validator],
    )
    serial_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Serial number'),
    )
    device_type = models.ForeignKey(
        'core.DeviceType',
        null=True,
        blank=True,
        verbose_name=_('Device type'),
        on_delete=models.PROTECT,
    )
    manufacturer = models.ForeignKey(
        'core.Manufacturer',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_('Manufacturer'),
    )
    series = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Model name'),
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Supplier')
    )
    is_licence = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Is license?'),
    )
    purchase_date = models.DateField(null=True, blank=True, verbose_name='Kaufdatum')
    warranty_expiration_date = models.DateField(null=True, blank=True, verbose_name='Garantieablaufdatum')
    maintenance_contract_expiration_date = models.DateField(null=True, blank=True, verbose_name='Ablaufdatum Lizenz- oder Wartungsvertrag')
    cost_centre = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Cost centre'))
    book_value = models.CharField(max_length=255, null=True, blank=True, verbose_name='Buchwert')

    note = models.TextField(null=True, blank=True, verbose_name='Notiz')
    mac_address = models.CharField(max_length=255, null=True, blank=True, verbose_name='Haupt-Mac-Adresse')
    extra_mac_addresses = models.TextField(null=True, blank=True, verbose_name='Weitere Mac-Adressen')
    nick_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Nickname / C-Name')
    is_legacy = models.BooleanField(default=False, verbose_name='Legacy-Device')

    is_lentable = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Is loanable?'),
    )
    is_imported = models.BooleanField(default=False, verbose_name='Via CSV-Import angelegt?')
    imported_by = models.ForeignKey(
        'core.ImporterList',
        null=True,
        blank=True,
        verbose_name='Importiert via',
        on_delete=models.SET_NULL,
    )
    qrcode = models.FileField(
        upload_to=f'{settings.QRCODE_DIR}/',
        blank=True,
        null=True,
        storage=OverwriteStorage(),
    )
    order_number = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Bestellnummer (SAP)",
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
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        ordering = ['-modified_at', 'edv_id']
        indexes = [
            models.Index(fields=["edv_id", "sap_id", "modified_at"]),
        ]

    def __repr__(self):
        return str(self.uuid)

    def __str__(self):
        identifier = 'n/a'
        if self.edv_id:
            identifier = self.edv_id
        elif self.sap_id:
            identifier = self.sap_id
        return str(identifier)

    def save(self, *args, **kwargs):
        if not self.qrcode:
            qrcode = uuid2qrcode(self.uuid, infix=settings.QRCODE_INFIXES.get('device'))
            self.qrcode.save(qrcode.filename, qrcode.fileobj, save=False)
        super().save(*args, **kwargs)

    def get_latest_note(self):
        """
        Returns the latest note of the related room and the current inventory.
        :return:
        """
        note = self.device_notes.filter(inventory__is_active=True).order_by('-created_at').first()
        return note

    def has_record_notes(self):
        return self.record_set.exclude(note__isnull=True).exclude(note__exact='').exists()

    @property
    def get_is_currently_lented(self):
        if not self.active_record:
            return False
        else:
            return all([
                self.active_record.is_type_lent,
                self.active_record.lent_end_date is None,
            ])

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

    def get_edv_id(self):
        """
        Returns the edv id or a "blank" string (used for the model admins)
        :param obj:
        :return:
        """
        return self.edv_id or '----'
    get_edv_id.short_description = 'EDV ID'

    # TODO: merge get_current_record_infos and get_record_add_links
    @property
    def get_current_record_infos(self):
        """
        Returns a list of dicts with infos for the current state of the
        device.
        """
        from .record import Record

        current_record_infos = []
        active_record = self.active_record

        if not active_record:
            current_record_infos.append(dict(
                label="No current record",
                css_classes="btn btn-warning disabled",
            ))
        else:
            if active_record.room:
                current_record_infos.append(dict(
                    css_classes="btn btn-info",
                    title="{text} {obj}".format(text=_('In room'), obj=active_record.room.number),
                    url=f"{reverse('admin:core_device_changelist')}?active_record__room__id__exact={active_record.room.id}",
                    label=active_record.room.number,
                ))

            # Common infos for all record types
            active_record_type = active_record.record_type
            record_type_info = {}

            if active_record_type == Record.INROOM:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    title=_("Relocate device"),
                    url=f"{reverse('core:core_devices_relocate')}?ids={self.pk}",
                    label=active_record.get_record_type_display,
                )
            elif active_record_type == Record.LENT:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    url=reverse("admin:core_lentrecord_change", args=[active_record.pk]),
                    label=f"an {active_record.person }",
                    title=_("Edit lending"),
                )
            elif active_record_type == Record.ORDERED:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    label=active_record.get_record_type_display,
                )
            elif active_record_type == Record.REMOVED:
                record_type_info = dict(
                    css_classes="btn btn-warning",
                    url=reverse("admin:core_record_change", args=[active_record.pk]),
                    label=active_record.get_record_type_display,
                )
            elif active_record_type == Record.LOST:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f"{reverse('admin:core_record_changelist')}?device__id__exact={self.pk}",
                    label=active_record.get_record_type_display,
                    title=_("Previous records for this device"),
                )
            else:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f'{reverse("admin:core_record_changelist")}?device__id__exact={self.pk}',
                    label=_("Unknown record type! Contact your administrator!"),
                )

            current_record_infos.append(record_type_info)

        return current_record_infos

    @property
    def get_record_add_links(self):
        """
        Returns a list of dicts each representing an add link in order to display
        dropdowns to create records for a given device.
        """
        from .record import Record

        add_links = []

        for record_value, record_label in Record.RECORD_TYPE_CHOICES:
            if record_value == Record.ORDERED:
                continue
            elif record_value == Record.REMOVED and self.active_record and self.active_record.record_type == Record.REMOVED:
                # Do not let already removed devices removed again
                continue
            elif record_value == Record.LOST and self.active_record and self.active_record.record_type == Record.LOST:
                # Lost records could not be lost again
                continue
            elif record_value == Record.LENT:
                if self.active_record and self.active_record.record_type == Record.LENT:
                    add_links.append(dict(
                        url=reverse("admin:core_lentrecord_change", args=[self.active_record.pk]),
                        label=_('Lending'),
                    ))
                elif  self.active_record and self.is_lentable:
                    add_links.append(dict(
                        url=reverse('admin:core_lentrecord_change', args=[self.active_record.pk]),
                        label=_('Lend'),
                    ))
            else:
                add_links.append(dict(
                    label=record_label,
                    url=f"{Record.get_proxy_model_by_record_type(record_value).get_admin_action_url()}?device={self.id}"
                ))

        return add_links
