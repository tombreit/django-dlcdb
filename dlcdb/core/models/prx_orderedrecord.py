# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.utils.translation import gettext_lazy as _

from .record import Record


class OrderedRecordManager(models.Manager):
    """
    Model Manager that filters the default record queryset
    based on the type.
    """

    def get_queryset(self):
        return super().get_queryset().filter(record_type=Record.ORDERED)


class OrderedRecord(Record):
    class Meta:
        proxy = True
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    objects = OrderedRecordManager()

    def save(self, **kwargs):
        self.record_type = Record.ORDERED
        super().save(**kwargs)
