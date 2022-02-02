from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models

from .record import Record


class InRoomRecordManager(models.Manager):
    """
    Model Manager that filters the default record queryset
    based on the type.
    """

    def get_queryset(self):
        return super().get_queryset().filter(
            record_type=Record.INROOM
        )


class InRoomRecord(Record):
    class Meta:
        proxy = True
        verbose_name = 'Raumzuweisung'
        verbose_name_plural = 'Raumzuweisungen'

    objects = InRoomRecordManager()

    def clean(self):
        if self.room is None:
            raise ValidationError('A room must be set!')

    def save(self, *args, **kwargs):
        self.record_type = Record.INROOM
        super().save(*args, **kwargs)
