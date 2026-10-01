# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Kept apart from models.py: core's models import TenantAwareModel, while
tenants.models imports core's AuditBaseModel. With both in models.py, loading
the tenants app first would import a half-loaded tenants.models.
"""

from django.db import models


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
