# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.db.models.functions import Lower


class Tenant(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
    )

    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        help_text="The groups which define this tenant.",
    )

    contact_email = models.EmailField(
        blank=True,
        help_text=(
            "Responsible contact/IT address for this tenant. Receives the overdue-"
            "lending copies (CC or reroute) for this tenant's devices and is shown in "
            "email footers. Falls back to the Branding IT dept email, then "
            "DEFAULT_FROM_EMAIL."
        ),
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

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = [Lower("name")]


class TenantAwareModel(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        # A tenant with devices cannot be deleted: SET_NULL would orphan its
        # devices, which then are invisible to every tenant-scoped user.
        on_delete=models.PROTECT,
        # Nullable for legacy devices only; forms require a tenant.
        null=True,
        # blank=True,
    )

    class Meta:
        abstract = True
