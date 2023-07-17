import uuid

from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from simple_history.models import HistoricalRecords

from dlcdb.inventory.utils import uuid2qrcode
from dlcdb.tenants.models import TenantAwareModel

from ..ui_helpers import UIRecordActionSnippetContext
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

    @property
    def get_record_action_snippet(self):
        return UIRecordActionSnippetContext(device_obj=self)
