from django.db import models

from .abstracts import SoftDeleteAuditBaseModel


class DeviceType(SoftDeleteAuditBaseModel):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Name')
    prefix = models.CharField(max_length=255, null=True, blank=True, verbose_name='Präfix')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Gerätetyp'
        verbose_name_plural = 'Gerätetypen'

    def __str__(self):
        return self.name
