# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..core.models.abstracts import SingletonBaseModel
from ..core.models import Device


class LicenseAsset(Device):
    """
    Proxy model for Device to represent a license asset. Used to assign
    dedicated permissions for "license-management-only users".
    """

    class Meta:
        proxy = True


class LicensesConfiguration(SingletonBaseModel):
    default_subscribers = models.ManyToManyField(
        "core.Person",
        related_name="+",
        blank=True,
        help_text=_("These subscribers will be added to all new licenses by default."),
    )

    def __str__(self):
        return "Licenses configuration"

    class Meta:
        verbose_name = _("Licenses configuration")
        verbose_name_plural = _("Licenses configuration")
