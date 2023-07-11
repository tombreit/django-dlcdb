import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .abstracts import AuditBaseModel
from .device import Device
from .room import Room
from .person import Person
from .inventory import Inventory


# Verbleib des Gerätes nach Ausmusterung
SOLD = 'SLD'
SCRAPPED = 'SCR'
SURRENDERED = 'SRD'
STOLEN = 'STL'
DUPLICATE = 'DPL'

DEVICE_DISPOSITION_CHOICES = [
    (SOLD, _('Sold')),
    (SCRAPPED, _('Scrapped')),
    (SURRENDERED, _('Surrendered')),
    (STOLEN, _('Stolen')),
    (DUPLICATE, _('Duplicate')),
]


class RecordQuerySet(models.QuerySet):
    def active_records(self):
        return self.filter(is_active=True)


class RecordManager(models.Manager):
    def get_queryset(self):
        return RecordQuerySet(self.model, using=self._db)

    def active_records(self):
        return self.get_queryset().active_records()


class Record(AuditBaseModel):

    # New record types/proxys must be added to:
    # * RECORD_TYPE_CHOICES
    # * RECORD_TYPE_CLASSES
    ORDERED = 'ORDERED'
    INROOM = 'INROOM'
    LENT = 'LENT'
    LOST = 'LOST'
    REMOVED = 'REMOVED'
    RECORD_TYPE_CHOICES = [
        (ORDERED, 'BESTELLT'),
        (INROOM, 'LOKALISIERT'),
        (LENT, 'VERLIEHEN'),
        (LOST, 'NICHT AUFFINDBAR'),
        (REMOVED, 'ENTFERNT'),
    ]

    device = models.ForeignKey(
        Device,
        verbose_name='Device',
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Aktiv',
    )
    effective_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Replaced by the next record at this timestamp."
    )

    # todo: implement field validator for record_type: must be one of...
    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPE_CHOICES,
        blank=False,
        db_index=True,
        verbose_name='Record Typ',
    )
    note = models.TextField(
        blank=True,
        verbose_name='Bemerkung (Record)',
    )
    # Licences could be bound to persons or devices
    assigned_device = models.ForeignKey(
        'core.Device',
        null=True,
        blank=True,
        related_name='assigned_device',
        limit_choices_to={'is_licence': False},
        on_delete=models.CASCADE,
        verbose_name='Zugeordnetes Device',
    )
    # Inventory
    inventory = models.ForeignKey(Inventory, null=True, blank=True, verbose_name='Inventur', on_delete=models.SET_NULL)
    # LentRecord
    person = models.ForeignKey(Person, null=True, blank=True, verbose_name='Person', on_delete=models.SET_NULL)
    lent_start_date = models.DateField(null=True, blank=True, verbose_name='Verleihbeginn')
    lent_desired_end_date = models.DateField(null=True, blank=True, verbose_name='Soll-Rückgabedatum')
    lent_end_date = models.DateField(
        null=True, blank=True, verbose_name='Zurückgegeben am',
        help_text='Mit dem Setzen ist der Verleih abgeschlossen'
    )
    lent_note = models.TextField(blank=True, verbose_name='Interne Bemerkung (Ausleihe)')
    lent_reason = models.TextField(blank=True, verbose_name='Ausleihgrund')
    lent_accessories = models.TextField(blank=True, verbose_name='Zubehör')

    # InRoomRecord
    room = models.ForeignKey(
        Room,
        null=True,
        blank=True,
        verbose_name=_('Room'),
        on_delete=models.PROTECT,
    )
    # Bestellvorgang
    date_of_purchase = models.DateField(null=True, blank=True, verbose_name='Bestelldatum')

    # REMOVED
    disposition_state = models.CharField(
        max_length=3,
        choices=DEVICE_DISPOSITION_CHOICES,
        blank=True,
        verbose_name=_('Whereabouts after decommissioning'),
    )
    removed_info = models.TextField(null=True, blank=True, verbose_name='Verbleib (removed_info)')
    removed_date = models.DateTimeField(null=True, blank=True, editable=False, verbose_name='Entfernt am')
    attachments = models.ManyToManyField(
        'core.Attachment',
        blank=True,
    )

    # objects = models.Manager()  # The default manager.
    objects = RecordManager()  # Custom records only manager

    class Meta:
        verbose_name = 'Record'
        verbose_name_plural = 'Records'
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid_lent_desired_end_date",
                check=Q(lent_desired_end_date__lte=datetime.datetime.strptime(settings.MAX_FUTURE_LENT_DESIRED_END_DATE, '%Y-%m-%d')),
            )
        ]

    def update_active_record_on_device(self):
        related_device = self.device
        related_device.active_record = self
        related_device.save()

    def __str__(self):
        return str(self.pk)

    def clean(self):
        if not self._meta.proxy:
            raise ValidationError('Records must be created via a proxy model. Creating plain records is not allowed. Hint: Create a new record.')

    def save(self, *args, **kwargs):
        """
        Always set the most recent record (the one which is created) as active for
        the related device.
        :return:
        """

        # set is active if instance is created
        is_new_record = self._state.adding
        if is_new_record:
            # Set all existing records to non active
            # qs.update() does not call the custom save method, does not
            # emit any signals and did not update the auto_now field so we
            # need to explictly set the modified_at field.
            # https://docs.djangoproject.com/en/4.1/ref/models/querysets/#django.db.models.query.QuerySet.update
            Record.objects.filter(device=self.device).update(
                is_active=False,
                effective_until=timezone.now(),
            )

            # As an alternative to qs.update():
            # for device_record in Record.objects.filter(device=self.device):
            #     if device_record.is_active == True:
            #         device_record.is_active == False
            #         device_record.save()

            # Set current record as active
            self.is_active = True

        super().save(*args, **kwargs)
        if is_new_record:
            self.update_active_record_on_device()

    def get_proxy_instance(self):
        """
        Return the concrete proxy model instance
        """
        modelclass = self.get_proxy_model()
        # query the concrete proy model instance
        return modelclass.objects.get(id=self.id)

    @staticmethod
    def get_proxy_model_by_record_type(record_type):
        from . import (
            OrderedRecord,
            InRoomRecord,
            LentRecord,
            LostRecord,
            RemovedRecord,
        )

        RECORD_TYPE_CLASSES = {
            'ORDERED': OrderedRecord,
            'INROOM': InRoomRecord,
            'LENT': LentRecord,
            'LOST': LostRecord,
            'REMOVED': RemovedRecord,
        }

        return RECORD_TYPE_CLASSES[record_type]


    def get_proxy_model(self):
        # print("self.recored_type: ", self.record_type)
        return Record.get_proxy_model_by_record_type(self.record_type)

    @classmethod
    def get_admin_action_url(cls):
        """
        Returns the admin add url. Whenever this method is called on a concrete
        proxy model it returns the add url of this proxy model.
        :return:
        """
        return reverse('admin:core_{model_name}_add'.format(
            model_name=cls.__name__.lower()
        ), args=[])

    def get_latest_note(self):
        """
        Returns the latest note of the related device.
        :return:
        """
        return self.device.device_notes.all().order_by('-created_at').first()

    @property
    def is_type_lent(self):
        return self.record_type == Record.LENT
