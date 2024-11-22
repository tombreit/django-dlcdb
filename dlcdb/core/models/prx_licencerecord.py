# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.db.models import Q

from .record import Record


class BaseLicenceRecordManager(models.Manager):
    def get_queryset(self):
        removed_records = Q(Q(record_type=Record.REMOVED))

        return (
            super()
            .get_queryset()
            .filter(
                is_active=True,
                device__is_licence=True,
            )
            .exclude(removed_records)
            .order_by("-modified_at")
        )


class LicenceRecord(Record):
    objects = BaseLicenceRecordManager()

    def get_human_title(self):
        return f"{self.device.manufacturer} - {self.device.series}"

    def __str__(self):
        return self.device.edv_id

    class Meta:
        proxy = True
        verbose_name = "Lizenz"
        verbose_name_plural = "Lizenzen"
