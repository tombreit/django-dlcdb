from django.db import models

from .record import Record


class OrderedRecordManager(models.Manager):
    """
    Model Manager that filters the default record queryset
    based on the type.
    """

    def get_queryset(self):
        return super().get_queryset().filter(
            record_type=Record.ORDERED
        )


class OrderedRecord(Record):
    class Meta:
        proxy = True
        verbose_name = 'Bestellung'
        verbose_name_plural = 'Bestellungen'

    objects = OrderedRecordManager()

    def save(self, **kwargs):
        self.record_type = Record.ORDERED
        super().save(**kwargs)
