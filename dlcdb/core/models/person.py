from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models import Count
from django.db.models.functions import Lower
from django.core.exceptions import ValidationError
from django.utils import timezone

from .abstracts import SoftDeleteAuditBaseModel


class PersonQuerySet(models.QuerySet):
    def active_contract_objects(self):
        return self.filter(
            udb_contract_planned_checkin__lte=timezone.now(),
            udb_contract_planned_checkout__gte=timezone.now(),
        )

    def smallstuff_person_objects(self):
        """
        Queryset which contains all active persons or persons who
        have some smallstuff things assigned and not yet returned.
        """
        has_active_contract_condition = Q(
            Q(udb_contract_planned_checkin__lte=timezone.now()) & Q(udb_contract_planned_checkout__gte=timezone.now())
        )

        qs = (
            self
            .annotate(assigned_things_count=Count(
                'assignedthing',
                filter=Q(assignedthing__unassigned_at__isnull=True),
                distinct=True,
            ))
            .annotate(
                unassigned_things_count=Count(
                    'assignedthing',
                    filter=Q(assignedthing__unassigned_at__isnull=False),
                    distinct=True,
            ))
            .filter(has_active_contract_condition | Q(assigned_things_count__gte=1)
            )
        )

        return qs


class ActiveContractObjectsManager(models.Manager):
    def get_queryset(self):
        return PersonQuerySet(self.model, using=self._db).active_contract_objects()


class SmallstuffPersonObjectsManager(models.Manager):
    def get_queryset(self):
        return PersonQuerySet(self.model, using=self._db).smallstuff_person_objects()


class ActiveContractObjectsBaseModel(models.Model):
    """
    https://docs.djangoproject.com/en/4.0/topics/db/managers/#custom-managers-and-model-inheritance
    """
    active_contract_objects = ActiveContractObjectsManager()
    smallstuff_person_objects = SmallstuffPersonObjectsManager()

    class Meta:
        abstract = True


class Person(SoftDeleteAuditBaseModel, ActiveContractObjectsBaseModel):

    DEPARTMENT_CHOICES = (
        ('edv', 'EDV'),
        ('bib', 'Bibliothek'),
        ('vrw', 'Verwaltung'),
        ('str', 'Strafrecht'),
        ('krm', 'Kriminologie'),
        ('psl', 'Öffentliches Recht/Public Law'),
        ('htk', 'Haustechnik'),
        ('pic', 'RG Personality, Identity, and Crime'),
        ('scc', 'RG Space, Contexts, and Crime'),
        ('rgs', 'RG Strafrechtstheorie'),
    )

    first_name = models.CharField(max_length=255, verbose_name='Vorname')
    last_name = models.CharField(max_length=255, verbose_name='Nachname')
    email = models.EmailField(
        blank=False,
        null=True,
        unique=True,
        help_text='IMMER eine Email-Adresse angeben, da wir sonst die Ausleiher nicht anschreiben können.',
    )
    department = models.CharField(
        max_length=3,
        choices=DEPARTMENT_CHOICES,
        blank=True,
    )

    # Additional UDB mirrored fields, all optional, updated by a cron task:
    udb_data_updated_at = models.DateTimeField(
        editable=False,
        null=True,
    )
    udb_person_first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    udb_person_last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    udb_person_email_private = models.EmailField(
        unique=True,
        max_length=320,
        blank=True,
        null=True,  # we need null=True to have unique=True together with missing values, stored as null
    )
    udb_person_email_internal_business = models.EmailField(
        unique=True,
        max_length=320,
        blank=True,
        null=True,
    )
    udb_person_image = models.ImageField(
        blank=True,
        upload_to=f"{settings.PERSON_IMAGE_UPLOAD_DIR}/"
    )
    # TODO: Use stay-dates instead of individual contract dates to avoid
    # please-return notifications if a follow up contract exists.
    udb_person_uuid = models.CharField(max_length=255, blank=True, null=True, unique=True)
    udb_contract_organization_unit = models.CharField(max_length=255, blank=True)
    udb_contract_planned_checkin = models.DateField(blank=True, null=True)
    udb_contract_planned_checkout = models.DateField(blank=True, null=True)
    udb_contract_organization_unit = models.CharField(max_length=255, blank=True)
    udb_contract_contract_type = models.CharField(max_length=255, blank=True)
    udb_contract_organizational_positions = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Person'
        verbose_name_plural = 'Personen'
        # unique_together = ['last_name', 'first_name']
        constraints = [
            models.UniqueConstraint(Lower('first_name'), Lower('last_name'), name='unique_dlcdb_person_name'),
            models.UniqueConstraint(Lower('udb_person_first_name'), Lower('udb_person_last_name'), name='unique_udb_person_name'),
        ]

    def __str__(self):
        return '{last_name}{delimiter}{first_name}'.format(first_name=self.first_name, last_name=self.last_name, delimiter=", " if self.first_name else "")

    def clean(self):
        if Person.only_softdeleted_objects.filter(email=self.email).exists():
            raise ValidationError('A soft-deleted person with this email address already exists. Please contact your IT;-)')
