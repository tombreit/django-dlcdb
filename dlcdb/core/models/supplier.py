from django.db import models
from django.db.models.functions import Upper
from django.utils.translation import gettext_lazy as _


class Supplier(models.Model):
    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Name',
        unique=True,
    )
    contact = models.TextField(
        blank=True,
        help_text=_("Contact and support information: contact persons, hotlines, mail addresses etc."),
    )
    note = models.TextField(
        blank=True,
    )

    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        ordering = [Upper('name')]

    def __str__(self):
        return self.name
