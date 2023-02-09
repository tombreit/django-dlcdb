from django.db import models
from django.utils.translation import gettext_lazy as _

from .abstracts import SoftDeleteAuditBaseModel


class DeviceType(SoftDeleteAuditBaseModel):
    name = models.CharField(
        max_length=255,
        blank=False,
    )
    prefix = models.CharField(
        max_length=255,
        blank=True,
    )
    note = models.TextField(
        blank=True,
    )
    class Meta:
        ordering = ('name',)
        verbose_name = _('Device Type')
        verbose_name_plural = _('Device Types')

    def __str__(self):
        return self.name
