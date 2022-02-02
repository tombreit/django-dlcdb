from datetime import datetime

from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from .record import Record
from .room import Room


class BaseLicenceRecordManager(models.Manager):

    def get_queryset(self):

        removed_records = Q(
            Q(record_type=Record.REMOVED)
        )

        return (
            super()
            .get_queryset()
            .filter(
                is_active=True,
                device__is_licence=True,
            )
            .exclude(
                removed_records
            )
            .order_by('-modified_at')
        )


class LicenceRecord(Record):
    objects = BaseLicenceRecordManager()

    def __str__(self):
        return self.device.edv_id

    class Meta:
        proxy = True
        verbose_name = 'Lizenz'
        verbose_name_plural = 'Lizenzen'
