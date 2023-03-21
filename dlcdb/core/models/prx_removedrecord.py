from django.urls import reverse
from django.db import models
from django.utils.timezone import now
from django.db.models import Q

from .record import Record


class RemovedRecordManager(models.Manager):
    """
    Model Manager that filters the default record queryset
    based on the type.
    """

    def get_queryset(self):
        return super().get_queryset().filter(
            record_type=Record.REMOVED
        )


class RemovedRecord(Record):
    class Meta:
        proxy = True
        verbose_name = 'Entfernt-Record'
        verbose_name_plural = 'Entfernt-Records'

    objects = RemovedRecordManager()

    def save(self, **kwargs):
        self.record_type = Record.REMOVED

        if not self.removed_date:
            self.removed_date = now()
        
        super().save(**kwargs)

    def __str__(self):
        return "{0}: {1}".format(
            self.device,
            self.get_disposition_state_display() or 'n/a',
        )
