from django.urls import reverse
from django.db import models
from django.db.models import Q

from .record import Record


class Manager(models.Manager):
    """
    Model Manager that filters the default record queryset
    based on the type.
    """

    def get_queryset(self):
        return super().get_queryset().filter(
            record_type=Record.LOST
        )


class LostRecord(Record):
    class Meta:
        proxy = True

    objects = Manager()

    def save(self, **kwargs):
        self.record_type = Record.LOST
        self.room = None
        super().save(**kwargs)
