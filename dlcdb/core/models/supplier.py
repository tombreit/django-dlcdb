from django.db import models
from django.db.models.functions import Upper


class Supplier(models.Model):
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Name',
        unique=True,
    )

    class Meta:
        verbose_name = 'Zulieferer'
        verbose_name_plural = 'Zulieferer'
        ordering = [Upper('name')]

    def __str__(self):
        return '{name}'.format(name=self.name)
