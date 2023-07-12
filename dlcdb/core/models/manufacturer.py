from django.db import models
from django.db.models.functions import Lower
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _


class Manufacturer(models.Model):
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Name'),
        unique=True,
    )
    note = models.TextField(
        blank=True,
        verbose_name=_('Note'),
    )

    class Meta:
        verbose_name = _('Manufacturer')
        verbose_name_plural = _('Manufacturers')
        ordering = [Lower('name')]
        constraints = [
            UniqueConstraint(
                Lower('name'),
                name='manufacturer_name_unique',
            ),
        ]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f'{self.name}'
