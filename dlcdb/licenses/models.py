# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from functools import reduce
from operator import or_

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..core.models import Device, DeviceType
from ..core.models.abstracts import SingletonBaseModel

LICENSE_DEVICE_TYPE_PREFIXES = ("Lizenz::", "License::", "Licence::")


def license_device_types():
    """
    The device types offered for a licence, in the licence form and in the
    licence list's type filter: those whose name starts with one of
    ``LICENSE_DEVICE_TYPE_PREFIXES``. Whether a device is a licence is decided
    by ``Device.is_licence``, not by its type.
    """
    return DeviceType.objects.filter(
        reduce(or_, (Q(name__startswith=prefix) for prefix in LICENSE_DEVICE_TYPE_PREFIXES))
    )


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
