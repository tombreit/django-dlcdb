from django.db import models
from django.db.models.functions import Lower

from .managers import TenantManager


class Tenant(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
    )

    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        help_text='The groups which define this tenant.',
    )

    # is_super_tenant = models.BooleanField(
    #     default=False,
    #     help_text="If set to True, users of this tenant could view and edit all assets.",
    # )

    # abbreviation = models.CharField(
    #     max_length=3,
    #     blank=False,
    #     unique=True,
    #     verbose_name='Abkürzung',
    #     help_text='Like "IT" or "VRL" etc.'
    # )

    # @classmethod
    # def get_default_pk(cls):
    #     obj, created = cls.objects.get_or_create(
    #         title='IT Department',
    #         defaults=dict(abbreviation='IT'),
    #     )
    #     return obj.pk

    objects = TenantManager()

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = [Lower('name')]


class TenantAwareModel(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        # blank=True,
    )

    class Meta:
        abstract = True
