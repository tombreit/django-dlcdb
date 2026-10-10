# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from .abstracts import SoftDeleteAuditBaseModel


class DeviceType(SoftDeleteAuditBaseModel):
    DEFAULT_ICON = "bi-pc-display"

    name = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_("Name"),
    )
    prefix = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Prefix"),
    )
    icon = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("Icon"),
        # format_lazy, not "%": "%" would translate at import time into the default
        # language, and makemigrations would then see a changed help_text.
        help_text=format_lazy(
            _("Bootstrap Icons class, e.g. “bi-laptop”. See {url}."), url="https://icons.getbootstrap.com/"
        ),
    )
    note = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _("Device Type")
        verbose_name_plural = _("Device Types")
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

    @property
    def icon_class(self):
        return self.icon or self.DEFAULT_ICON
