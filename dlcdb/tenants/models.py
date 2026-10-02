# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from dlcdb.core.models.abstracts import AuditBaseModel


class Tenant(AuditBaseModel):
    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("Name"),
    )

    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        help_text=_("Members of these groups see this tenant's devices."),
    )

    contact_email = models.EmailField(
        blank=True,
        verbose_name=_("Contact email"),
        help_text=_(
            "Receives the overdue-lending reminders for this tenant's devices, as a copy or instead of "
            "the borrower (see the lending configuration), and is shown in email footers. Falls back "
            "to the IT department email in Branding."
        ),
    )

    # Records every create, rename, group change and delete: the groups decide
    # who sees this tenant's devices.
    history = HistoricalRecords(m2m_fields=["groups"])

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = [Lower("name")]
